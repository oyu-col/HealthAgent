import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowUpRight,
  ChevronDown,
  FileText,
  HeartPulse,
  Leaf,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  PanelRight,
  Plus,
  Search,
  ShieldCheck,
  Sun,
  X,
} from "lucide-react";
import { ApiError, requestJson } from "./lib/api";
import { errorMessage, useResource } from "./lib/hooks";
import type {
  HealthDocument,
  MemoryData,
  Session,
  Thread,
  View,
} from "./lib/types";
import { Brand, ErrorNotice, Loading } from "./components/ui";
import { Chat } from "./components/Chat";
import { Records } from "./components/Records";
import { Documents } from "./components/Documents";
import { Memory, preferenceLabels } from "./components/Memory";

const navigation = [
  { id: "chat", label: "健康对话", icon: MessageSquare },
  { id: "records", label: "健康记录", icon: HeartPulse },
  { id: "documents", label: "我的文档", icon: FileText },
  { id: "memory", label: "长期偏好", icon: Leaf },
] as const;
type Route = { view: View; threadId?: string };
function readRoute(): Route {
  const [view, id] = location.hash.replace(/^#\/?/, "").split("/");
  if (view === "records" || view === "documents" || view === "memory")
    return { view };
  return {
    view: "chat",
    ...(id && /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(id)
      ? { threadId: id }
      : {}),
  };
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [token, setToken] = useState("");
  const [input, setInput] = useState("");
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const connection = useRef<AbortController | null>(null);
  const connect = useCallback(async (credential: string) => {
    connection.current?.abort();
    const controller = new AbortController();
    connection.current = controller;
    setSession(null);
    setConnecting(true);
    setError(null);
    try {
      const next = await requestJson<Session>("/api/session", credential, {
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setToken(credential);
        setInput("");
        setSession(next);
      }
    } catch (cause) {
      if (!controller.signal.aborted)
        setError(
          cause instanceof ApiError && cause.status === 401
            ? "请输入服务端配置的访问凭据以连接工作空间。"
            : errorMessage(cause),
        );
    } finally {
      if (!controller.signal.aborted) setConnecting(false);
    }
  }, []);
  useEffect(() => {
    void connect("");
    return () => connection.current?.abort();
  }, [connect]);
  function disconnect() {
    connection.current?.abort();
    setSession(null);
    setToken("");
    setInput("");
    setError(null);
    setConnecting(false);
    location.hash = "/chat";
  }
  if (!session)
    return (
      <main className="connection-screen">
        <div className="connection-card">
          <Brand />
          <span className="eyebrow">YOUR PERSONAL HEALTH SPACE</span>
          <h1>欢迎来到 HealthAgent</h1>
          <p>
            把日常记录、健康资料和每一次对话，
            <br />
            放进同一个专属工作空间。
          </p>
          {connecting ? (
            <Loading label="正在连接工作空间…" />
          ) : (
            <form
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                void connect(input.trim());
              }}
              className="form-stack"
            >
              {error && <ErrorNotice message={error} />}
              <label>
                访问凭据
                <input
                  type="password"
                  autoComplete="off"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="服务端访问令牌（本地模式可留空）"
                />
              </label>
              <button className="primary-button" type="submit">
                连接工作空间 <ArrowUpRight size={16} />
              </button>
              <small className="field-hint">
                凭据仅保留在当前页面内存中，关闭或刷新后需重新连接。
              </small>
            </form>
          )}
        </div>
        <p className="connection-footnote">
          <ShieldCheck size={14} />
          你的数据，由你掌握
        </p>
      </main>
    );
  return (
    <Workspace token={token} session={session} onDisconnect={disconnect} />
  );
}

function Workspace({
  token,
  session,
  onDisconnect,
}: {
  token: string;
  session: Session;
  onDisconnect: () => void;
}) {
  const [route, setRoute] = useState<Route>(readRoute);
  const [mobileNav, setMobileNav] = useState(false);
  const [narrow, setNarrow] = useState(
    () => window.matchMedia("(max-width: 760px)").matches,
  );
  const [context, setContext] = useState(false);
  const [dark, setDark] = useState(false);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState<{ text: string; key: number }>({
    text: "",
    key: 0,
  });
  const threads = useResource<{ threads: Thread[] }>("/api/threads", token);
  const refreshThreads = threads.reload;
  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const resized = () => setNarrow(media.matches);
    media.addEventListener("change", resized);
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("keydown", escape);
    return () => {
      media.removeEventListener("change", resized);
      window.removeEventListener("keydown", escape);
    };
  }, []);
  useEffect(() => {
    const changed = () => setRoute(readRoute());
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    return () => {
      delete document.documentElement.dataset.theme;
    };
  }, [dark]);
  const navigate = useCallback((view: View, threadId?: string) => {
    setRoute({ view, threadId });
    location.hash = `/${view}${threadId ? `/${threadId}` : ""}`;
    setMobileNav(false);
  }, []);
  const created = useCallback(
    (id: string) => {
      navigate("chat", id);
      refreshThreads();
    },
    [navigate, refreshThreads],
  );
  function newChat() {
    setDraft({ text: "", key: Date.now() });
    navigate("chat");
  }
  function ask(text: string) {
    setDraft({ text, key: Date.now() });
    navigate("chat");
  }
  const title = navigation.find((item) => item.id === route.view)?.label;
  return (
    <div className="workspace">
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="关闭导航"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileNav ? "open" : ""}`}
        aria-label="工作空间导航"
        aria-hidden={narrow && !mobileNav}
        inert={narrow && !mobileNav}
      >
        <div className="sidebar-brand">
          <Brand small />
          <strong>
            HealthAgent<span>个人健康工作台</span>
          </strong>
          <button
            className="icon-button mobile-only"
            aria-label="关闭导航"
            onClick={() => setMobileNav(false)}
          >
            <X size={18} />
          </button>
        </div>
        <button className="new-chat" onClick={newChat} disabled={busy}>
          <Plus size={18} />
          新对话<span>↗</span>
        </button>
        <nav>
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${route.view === id ? "active" : ""}`}
              onClick={() => navigate(id)}
              disabled={busy}
              aria-current={route.view === id ? "page" : undefined}
            >
              <Icon size={18} strokeWidth={1.7} />
              {label}
              {route.view === id && <span className="active-dot" />}
            </button>
          ))}
        </nav>
        <div className="history-heading">
          <span>最近对话</span>
          <MessageSquare size={13} />
        </div>
        <label className="history-search">
          <Search size={14} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索对话"
            aria-label="搜索对话"
          />
        </label>
        <div className="thread-list">
          {threads.error ? (
            <ErrorNotice message={threads.error} retry={threads.reload} />
          ) : threads.loading && !threads.data ? (
            <Loading />
          ) : threads.data?.threads.length ? (
            threads.data.threads
              .filter((thread) => (thread.title ?? "新对话").includes(query))
              .map((thread) => (
                <button
                  className={`thread-item ${route.threadId === thread.thread_id ? "selected" : ""}`}
                  key={thread.thread_id}
                  onClick={() => navigate("chat", thread.thread_id)}
                  disabled={busy}
                  title={thread.title ?? "新对话"}
                >
                  <span
                    className={`thread-dot ${thread.can_resume ? "pending" : ""}`}
                  />
                  <span>{thread.title || "新对话"}</span>
                </button>
              ))
          ) : (
            <p className="history-empty">
              从一个小问题开始，
              <br />
              对话会保存在这里。
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="private-note">
            <ShieldCheck size={15} />
            <span>专属于你的健康空间</span>
          </div>
          <button
            className="account-button"
            onClick={onDisconnect}
            aria-label="更换访问凭据"
          >
            <span className="avatar">
              {session.user_id.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{session.user_id}</strong>
              <small>已连接 · {session.timezone}</small>
            </span>
            <LogOut size={15} />
          </button>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-only"
              aria-label="打开导航"
              aria-expanded={mobileNav}
              onClick={() => setMobileNav(true)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">我的工作空间</span>
            <span className="breadcrumb-divider">/</span>
            <span>{title}</span>
            <ChevronDown size={12} className="muted" />
          </div>
          <div className="topbar-actions">
            <span
              className={`mode-badge ${session.model_mode === "fake" ? "demo" : ""}`}
              title={
                session.model_mode === "fake"
                  ? "使用确定性测试模型，不会生成真实健康分析。"
                  : "已连接服务端模型"
              }
            >
              <span />
              {session.model_mode === "fake" ? "演示模式" : "模型已连接"}
            </span>
            <button
              className="icon-button"
              aria-label={dark ? "切换浅色模式" : "切换深色模式"}
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button
              className={`icon-button ${context ? "pressed" : ""}`}
              aria-label="资料与偏好"
              aria-expanded={context}
              onClick={() => setContext(!context)}
            >
              <PanelRight size={18} />
            </button>
          </div>
        </header>
        <main className="main-surface">
          {route.view === "chat" ? (
            <Chat
              token={token}
              session={session}
              threadId={route.threadId}
              onThreadCreated={created}
              onThreadsChanged={threads.reload}
              onBusyChange={setBusy}
              onNavigate={navigate}
              initialDraft={draft}
            />
          ) : route.view === "records" ? (
            <Records token={token} session={session} />
          ) : route.view === "documents" ? (
            <Documents token={token} session={session} onAsk={ask} />
          ) : (
            <Memory token={token} session={session} />
          )}
        </main>
      </div>
      {context && (
        <ContextPanel
          token={token}
          onClose={() => setContext(false)}
          onNavigate={(view) => {
            if (!busy) {
              navigate(view);
              setContext(false);
            }
          }}
          busy={busy}
        />
      )}
    </div>
  );
}

function ContextPanel({
  token,
  onClose,
  onNavigate,
  busy,
}: {
  token: string;
  onClose: () => void;
  onNavigate: (view: View) => void;
  busy: boolean;
}) {
  const documents = useResource<{ documents: HealthDocument[] }>(
    "/api/documents",
    token,
  );
  const memory = useResource<MemoryData>("/api/memory", token);
  return (
    <aside className="context-panel" aria-label="资料与偏好面板">
      <header>
        <strong>资料与偏好</strong>
        <button
          className="icon-button"
          aria-label="关闭资料面板"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </header>
      <p>为每次交流，保留有用的上下文。</p>
      <div className="context-section">
        <h3>
          <FileText size={16} />
          我的文档
        </h3>
        {documents.loading ? (
          <Loading />
        ) : documents.error ? (
          <ErrorNotice message={documents.error} retry={documents.reload} />
        ) : documents.data?.documents.length ? (
          documents.data.documents.slice(0, 8).map((doc) => (
            <div className="context-row" key={doc.id}>
              <span>{doc.filename}</span>
              <small>
                {doc.index_status === "indexed" ? "可检索" : "未就绪"}
              </small>
            </div>
          ))
        ) : (
          <p className="muted">还没有上传文档。</p>
        )}
        <button
          className="text-button"
          disabled={busy}
          onClick={() => onNavigate("documents")}
        >
          管理文档 <ArrowUpRight size={14} />
        </button>
      </div>
      <div className="context-section">
        <h3>
          <Leaf size={16} />
          已记住的偏好
        </h3>
        {memory.loading ? (
          <Loading />
        ) : memory.error ? (
          <ErrorNotice message={memory.error} retry={memory.reload} />
        ) : memory.data?.preferences.length ? (
          memory.data.preferences.map((item) => (
            <div className="context-row" key={item.key}>
              <span>{preferenceLabels[item.key] ?? item.key}</span>
              <small>{preferenceLabels[item.value] ?? item.value}</small>
            </div>
          ))
        ) : (
          <p className="muted">由你决定值得记住的事。</p>
        )}
        <button
          className="text-button"
          disabled={busy}
          onClick={() => onNavigate("memory")}
        >
          管理偏好 <ArrowUpRight size={14} />
        </button>
      </div>
      <div className="context-footnote">
        <ShieldCheck size={17} />
        <p>
          这里只展示已保存的资料与偏好。回答中使用的证据以实际检索结果为准。
        </p>
      </div>
    </aside>
  );
}
