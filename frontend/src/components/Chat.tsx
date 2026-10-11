import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowRight,
  ArrowUp,
  Check,
  FileText,
  HeartPulse,
  Leaf,
  LoaderCircle,
  Paperclip,
  RotateCcw,
  ShieldCheck,
  Square,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, requestJson, streamChat } from "../lib/api";
import { errorMessage } from "../lib/hooks";
import type {
  ChatInput,
  ChatResult,
  Message,
  Session,
  StreamEvent,
  ThreadState,
  View,
} from "../lib/types";
import { Brand, ErrorNotice, Loading } from "./ui";
import { TraceDialog } from "./TraceDialog";

type Props = {
  token: string;
  session: Session;
  threadId?: string;
  onThreadCreated: (id: string) => void;
  onThreadsChanged: () => void;
  onBusyChange: (busy: boolean) => void;
  onNavigate: (view: View) => void;
  initialDraft: { text: string; key: number };
};
const toolNames: Record<string, string> = {
  add_health_metric: "保存身体指标",
  query_health_metrics: "查询身体指标",
  add_diet_record: "保存饮食记录",
  query_diet_records: "查询饮食记录",
  add_exercise_record: "保存运动记录",
  query_exercise_records: "查询运动记录",
  query_health_documents: "检索私人文档",
  search_health_knowledge: "检索健康知识",
  calculate_health_trend: "计算指标趋势",
  delegate_health_task: "委派专业助手",
};

function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
        img: ({ alt }) => (
          <span className="muted">[图片：{alt || "未加载外部图片"}]</span>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}

export function Chat({
  token,
  session,
  threadId,
  onThreadCreated,
  onThreadsChanged,
  onBusyChange,
  onNavigate,
  initialDraft,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState(initialDraft.text);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState("");
  const [incomplete, setIncomplete] = useState(false);
  const [tools, setTools] = useState<
    { id: string; name: string; status: string }[]
  >([]);
  const [recoverable, setRecoverable] = useState(false);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const active = useRef<{
    input: ChatInput;
    threadId?: string;
    controller: AbortController;
  } | null>(null);
  const resumeId = useRef<string | null>(null);
  const historyController = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const bottom = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const changeBusy = useCallback(
    (value: boolean) => {
      setBusy(value);
      onBusyChange(value);
    },
    [onBusyChange],
  );
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      active.current?.controller.abort();
      historyController.current?.abort();
      onBusyChange(false);
    };
  }, [onBusyChange]);
  useEffect(() => {
    if (threadId && active.current?.threadId === threadId) return;
    historyController.current?.abort();
    active.current?.controller.abort();
    active.current = null;
    setMessages([]);
    setStreaming("");
    setTools([]);
    setError(null);
    setIncomplete(false);
    setRecoverable(false);
    setTraceId(null);
    setShowTrace(false);
    setBlocked(false);
    resumeId.current = null;
    changeBusy(false);
    setDraft(threadId ? "" : initialDraft.text);
    if (!threadId) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    historyController.current = controller;
    setLoading(true);
    void requestJson<ThreadState>(`/api/threads/${threadId}`, token, {
      signal: controller.signal,
    })
      .then((state) => {
        if (!controller.signal.aborted) {
          setMessages(state.messages);
          setRecoverable(
            Boolean(state.can_resume) || state.status === "running",
          );
          resumeId.current = state.active_request_id;
          if (state.status === "failed" && !state.can_resume) {
            setBlocked(true);
            setError("该会话没有可恢复的执行节点，请新建对话后重试。");
          }
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [threadId, token, initialDraft.key, initialDraft.text, changeBusy]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, streaming, tools.length]);

  async function refreshRecovery(id?: string) {
    if (!id) {
      setRecoverable(Boolean(active.current));
      return;
    }
    try {
      const state = await requestJson<ThreadState>(`/api/threads/${id}`, token);
      if (alive.current && active.current?.threadId === id) {
        setRecoverable(Boolean(state.can_resume) || state.status === "running");
        resumeId.current = state.active_request_id;
        if (
          state.status === "idle" &&
          state.messages.at(-1)?.role === "assistant"
        ) {
          setMessages(state.messages);
          setStreaming("");
          setIncomplete(false);
          setError(null);
        }
        if (state.status === "failed" && !state.can_resume) {
          setBlocked(true);
          setError("该请求未完成，且没有可恢复的执行节点，请新建对话后重试。");
        }
      }
    } catch {
      if (alive.current) setRecoverable(true);
    }
  }
  function acceptResult(result: ChatResult) {
    setMessages((previous) => [
      ...previous,
      { role: "assistant", content: result.answer },
    ]);
    setStreaming("");
    setIncomplete(false);
    setRecoverable(false);
    setTraceId(result.trace_id);
    setError(null);
    onThreadsChanged();
  }
  async function send(retry = false) {
    if (
      busy ||
      loading ||
      blocked ||
      (recoverable && !retry) ||
      (!retry && !draft.trim())
    )
      return;
    const input =
      retry && active.current
        ? active.current.input
        : {
            message: draft.trim(),
            ...(threadId ? { thread_id: threadId } : {}),
            request_id: crypto.randomUUID(),
          };
    const controller = new AbortController();
    active.current = { input, threadId: input.thread_id, controller };
    resumeId.current = input.request_id;
    changeBusy(true);
    setError(null);
    setStreaming("");
    setTools([]);
    setIncomplete(false);
    setRecoverable(false);
    if (!retry) {
      setMessages((previous) => [
        ...previous,
        { role: "user", content: input.message },
      ]);
      setDraft("");
    }
    try {
      const result = await streamChat(
        input,
        token,
        (event: StreamEvent) => {
          if (!alive.current || controller.signal.aborted) return;
          const data = event.data;
          if (event.event === "run.started") {
            active.current!.threadId = data.thread_id!;
            setTraceId(data.trace_id);
            onThreadCreated(data.thread_id!);
          } else if (event.event === "message.delta")
            setStreaming((text) => text + (data.text ?? ""));
          else if (event.event === "tool.started")
            setTools((previous) => [
              ...previous,
              { id: data.tool_call_id!, name: data.name!, status: "running" },
            ]);
          else if (event.event === "tool.finished")
            setTools((previous) =>
              previous.map((tool) =>
                tool.id === data.tool_call_id
                  ? { ...tool, status: data.success ? "done" : "failed" }
                  : tool,
              ),
            );
        },
        controller.signal,
      );
      if (alive.current) acceptResult(result);
    } catch (cause) {
      if (!alive.current) return;
      if (cause instanceof ApiError) {
        if (cause.traceId) setTraceId(cause.traceId);
        if (cause.threadId) {
          active.current!.threadId = cause.threadId;
          onThreadCreated(cause.threadId);
        }
      }
      setIncomplete(true);
      setError(
        cause instanceof Error && cause.name === "AbortError"
          ? "已停止生成，当前内容尚未完成。可以恢复原请求。"
          : errorMessage(cause),
      );
      await refreshRecovery(active.current?.threadId);
    } finally {
      if (alive.current) {
        changeBusy(false);
        onThreadsChanged();
      }
    }
  }
  async function resume() {
    const id = active.current?.threadId ?? threadId;
    if (!id) {
      await send(true);
      return;
    }
    if (!resumeId.current || busy) return;
    const controller = new AbortController();
    active.current = {
      input: active.current?.input ?? {
        message: "",
        thread_id: id,
        request_id: resumeId.current,
      },
      threadId: id,
      controller,
    };
    changeBusy(true);
    setError(null);
    try {
      const result = await requestJson<ChatResult>(
        `/api/threads/${id}/resume`,
        token,
        {
          method: "POST",
          body: JSON.stringify({ request_id: resumeId.current }),
          signal: controller.signal,
        },
      );
      if (!alive.current) return;
      setStreaming("");
      setIncomplete(false);
      setRecoverable(false);
      setTraceId(result.trace_id);
      onThreadsChanged();
      try {
        const state = await requestJson<ThreadState>(
          `/api/threads/${id}`,
          token,
          { signal: controller.signal },
        );
        if (alive.current) setMessages(state.messages);
      } catch {
        if (alive.current && !controller.signal.aborted)
          setMessages((previous) => [
            ...previous,
            { role: "assistant", content: result.answer },
          ]);
      }
    } catch (cause) {
      if (alive.current) {
        setError(errorMessage(cause));
        setIncomplete(true);
        if (cause instanceof ApiError && cause.code === "resume_unavailable")
          setRecoverable(false);
      }
    } finally {
      if (alive.current) changeBusy(false);
    }
  }
  const welcome = !loading && messages.length === 0 && !busy;
  return (
    <div
      className={`chat-workspace ${welcome ? "is-welcome" : "has-messages"}`}
    >
      {welcome && (
        <div className="welcome">
          <div className="welcome-mark">
            <Brand />
            <span>每一天，都值得好好照顾自己</span>
          </div>
          <h1>
            从今天开始，
            <br />
            <span>更了解自己的健康。</span>
          </h1>
          <p>
            记录日常，整理资料，
            <br className="mobile-only" />
            让每一个健康问题都有上下文。
          </p>
        </div>
      )}
      {!welcome && (
        <div className="conversation" aria-label="对话消息">
          {loading && <Loading label="正在读取会话…" />}
          {messages.map((message, index) => (
            <article className={`message ${message.role}`} key={index}>
              {message.role === "assistant" && (
                <div className="message-heading">
                  <Brand small />
                  <strong>HealthAgent</strong>
                </div>
              )}
              <div className="message-body">
                {message.role === "assistant" ? (
                  <Markdown text={message.content} />
                ) : (
                  message.content
                )}
              </div>
            </article>
          ))}
          {tools.length > 0 && (
            <div className="tool-activity" aria-label="工具执行状态">
              {tools.map((tool, index) => (
                <span key={`${tool.id}-${index}`} className={tool.status}>
                  {tool.status === "running" && busy ? (
                    <LoaderCircle size={13} className="spin" />
                  ) : tool.status === "done" ? (
                    <Check size={13} />
                  ) : (
                    <Square size={11} />
                  )}
                  {toolNames[tool.name] ?? tool.name}
                  <small>
                    {tool.status === "failed"
                      ? "未完成"
                      : tool.status === "done"
                        ? "已完成"
                        : !busy
                          ? "已中断"
                          : "处理中"}
                  </small>
                </span>
              ))}
            </div>
          )}
          {(streaming || busy) && (
            <article className="message assistant">
              <div className="message-heading">
                <Brand small />
                <strong>HealthAgent</strong>
                {busy && (
                  <span className="thinking-label">
                    正在处理<span className="thinking-dots">···</span>
                  </span>
                )}
              </div>
              <div className={`message-body ${incomplete ? "unfinished" : ""}`}>
                {streaming ? (
                  <Markdown text={streaming} />
                ) : (
                  <span className="muted">正在整理你的问题…</span>
                )}
                {incomplete && (
                  <small className="incomplete-label">未完成的内容</small>
                )}
              </div>
            </article>
          )}
          {traceId && !busy && (
            <div className="trace-reference">
              <button onClick={() => setShowTrace(true)}>
                查看执行记录 <code>{traceId.slice(0, 8)}</code>
              </button>
            </div>
          )}
          <div ref={bottom} />
        </div>
      )}
      <div className="composer-area">
        {error && <ErrorNotice message={error} />}
        {recoverable && !busy && (
          <div className="resume-notice">
            <span>上一次请求尚未完成，请先恢复。</span>
            <button
              className="text-button"
              onClick={() => {
                void resume();
              }}
            >
              <RotateCcw size={15} />
              恢复请求
            </button>
          </div>
        )}
        <form
          className={`composer ${busy ? "generating" : ""}`}
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void send();
          }}
        >
          <textarea
            ref={composer}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="记录今天的状态，或聊聊你的健康问题…"
            aria-label="输入健康问题"
            maxLength={8000}
            rows={3}
            disabled={loading || recoverable || blocked}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                void send();
              }
            }}
          />
          <div className="composer-toolbar">
            <button
              type="button"
              className="icon-button"
              aria-label="上传健康文档"
              title="前往文档上传"
              disabled={busy}
              onClick={() => onNavigate("documents")}
            >
              <Paperclip size={19} />
            </button>
            <span className="composer-context">
              <span />
              {session.model_mode === "fake" ? "演示模型" : "健康助手"}
            </span>
            <span className="composer-hint">Shift + Enter 换行</span>
            {busy ? (
              <button
                type="button"
                className="send-button stop"
                aria-label="停止生成"
                onClick={() => active.current?.controller.abort()}
              >
                <Square size={15} fill="currentColor" />
              </button>
            ) : (
              <button
                type="submit"
                className="send-button"
                aria-label="发送消息"
                disabled={!draft.trim() || loading || recoverable || blocked}
              >
                <ArrowUp size={20} />
              </button>
            )}
          </div>
        </form>
        {welcome && (
          <>
            <div className="prompt-chips">
              <button
                onClick={() => {
                  setDraft("你可以帮我管理哪些健康信息？");
                  composer.current?.focus();
                }}
              >
                了解助手能做什么 <ArrowRight size={12} />
              </button>
              <button
                onClick={() => {
                  setDraft("请查看我最近的健康记录，数据不足时请告诉我。");
                  composer.current?.focus();
                }}
              >
                回顾最近的状态 <ArrowRight size={12} />
              </button>
            </div>
            <div className="welcome-cards">
              {[
                {
                  view: "records" as const,
                  icon: HeartPulse,
                  title: "记录日常",
                  text: "身体指标、饮食与运动",
                },
                {
                  view: "documents" as const,
                  icon: FileText,
                  title: "整理健康资料",
                  text: "上传报告，让提问有所依据",
                },
                {
                  view: "memory" as const,
                  icon: Leaf,
                  title: "记住你的偏好",
                  text: "让每一次对话更贴合你",
                },
              ].map(({ view, icon: Icon, title, text }) => (
                <button key={view} onClick={() => onNavigate(view)}>
                  <Icon size={22} strokeWidth={1.5} />
                  <strong>{title}</strong>
                  <span>{text}</span>
                  <ArrowRight size={15} />
                </button>
              ))}
            </div>
          </>
        )}
        <p className="chat-footnote">
          <ShieldCheck size={12} />
          {session.model_mode === "fake"
            ? "演示模型用于验证流程，不提供真实健康分析。"
            : "健康信息辅助，不能替代医生诊断。紧急情况请及时就医。"}
        </p>
      </div>
      {showTrace && traceId && (
        <TraceDialog
          traceId={traceId}
          token={token}
          onClose={() => setShowTrace(false)}
        />
      )}
    </div>
  );
}
