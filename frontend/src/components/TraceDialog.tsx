import { Activity, Clock3, GitBranch, RotateCcw } from "lucide-react";
import { useResource } from "../lib/hooks";
import { Dialog, ErrorNotice, Loading } from "./ui";

type TraceEvent = {
  seq: number;
  event: string;
  elapsed_ms: number;
  name?: string;
  agent_name?: string;
  success?: boolean;
  error_code?: string | null;
  latency_ms?: number;
  attempt?: number;
};
type Trace = {
  trace_id: string;
  status: string;
  termination_reason: string | null;
  latency_ms: number | null;
  model_calls: number | null;
  tool_calls: number | null;
  subagent_calls: number | null;
  retry_count: number | null;
  total_steps: number | null;
  task_kind: string;
  capture_complete: boolean;
  dropped_events: number;
  token_usage: {
    input_tokens: number | null;
    output_tokens: number | null;
    total_tokens: number | null;
    complete: boolean;
  };
  events: TraceEvent[];
};
const eventLabels: Record<string, string> = {
  "model.started": "开始模型调用",
  "model.finished": "模型调用结束",
  "tool.started": "开始工具调用",
  "tool.finished": "工具调用结束",
  "tool.retry": "工具重试",
  "model.retry": "模型重试",
  "delegation.started": "开始专业委派",
  "delegation.finished": "专业委派结束",
  "guardrail.blocked": "触发保护规则",
  "run.started": "开始执行",
  "run.finished": "执行结束",
  "cache.hit": "复用已有结果",
};
const statuses: Record<string, string> = {
  completed: "已完成",
  running: "执行中",
  failed: "未完成",
  cancelled: "已取消",
  interrupted: "已中断",
};
function duration(ms: number | null) {
  return ms == null
    ? "—"
    : ms < 1000
      ? `${Math.round(ms)} ms`
      : `${(ms / 1000).toFixed(2)} s`;
}

export function TraceDialog({
  traceId,
  token,
  onClose,
}: {
  traceId: string;
  token: string;
  onClose: () => void;
}) {
  const resource = useResource<Trace>(
    `/api/traces/${encodeURIComponent(traceId)}`,
    token,
  );
  const trace = resource.data;
  return (
    <Dialog title="执行记录" wide onClose={onClose}>
      <div className="trace-content">
        {resource.loading ? (
          <Loading label="读取执行记录…" />
        ) : resource.error ? (
          <ErrorNotice message={resource.error} retry={resource.reload} />
        ) : (
          trace && (
            <>
              <div className="trace-summary">
                <span
                  className={`status-badge ${trace.status === "completed" ? "ready" : "neutral"}`}
                >
                  {statuses[trace.status] ?? trace.status}
                </span>
                <code>{trace.trace_id}</code>
              </div>
              <div className="trace-metrics">
                {[
                  {
                    icon: Clock3,
                    label: "总耗时",
                    value: duration(trace.latency_ms),
                  },
                  {
                    icon: Activity,
                    label: "模型 / 工具",
                    value: `${trace.model_calls ?? "—"} / ${trace.tool_calls ?? "—"}`,
                  },
                  {
                    icon: GitBranch,
                    label: "专业委派",
                    value: trace.subagent_calls ?? "—",
                  },
                  {
                    icon: RotateCcw,
                    label: "可观测重试",
                    value: trace.retry_count ?? "—",
                  },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label}>
                    <Icon size={16} />
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              <div className="trace-details">
                <p>
                  终止原因 <code>{trace.termination_reason ?? "尚未结束"}</code>
                </p>
                <p>
                  Token 用量{" "}
                  <span>
                    {trace.token_usage.complete
                      ? trace.token_usage.total_tokens
                      : "不可完整观测"}
                  </span>
                </p>
                <p>
                  执行类型{" "}
                  <span>
                    {trace.task_kind === "cached"
                      ? "复用持久化结果"
                      : trace.task_kind === "resume"
                        ? "恢复执行"
                        : "新一轮对话"}
                  </span>
                </p>
              </div>
              {(!trace.capture_complete || trace.dropped_events > 0) && (
                <p className="field-hint">
                  记录不完整或事件已达到保存上限，缺失部分不能视为未发生。
                </p>
              )}
              <ol className="trace-timeline">
                {trace.events.map((event) => (
                  <li key={event.seq}>
                    <span
                      className={`event-dot ${event.success === false ? "failed" : ""}`}
                    />
                    <div>
                      <strong>{eventLabels[event.event] ?? event.event}</strong>
                      <span>
                        {[
                          event.success === false
                            ? "失败"
                            : event.success === true
                              ? "成功"
                              : null,
                          event.agent_name,
                          event.name,
                          event.error_code,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </div>
                    <small>{duration(event.elapsed_ms)}</small>
                  </li>
                ))}
              </ol>
              <p className="field-hint">
                仅展示执行元数据，不保存问题、健康原文或工具参数。模型服务 SDK
                内部重试可能不可见。
              </p>
            </>
          )
        )}
      </div>
    </Dialog>
  );
}
