import { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronRight,
  Globe2,
  Leaf,
  MessageSquare,
  RefreshCw,
  Sparkles,
  Trash2,
  Footprints,
} from "lucide-react";
import { requestJson } from "../lib/api";
import { errorMessage, formatDate, useResource } from "../lib/hooks";
import type { MemoryData, Session } from "../lib/types";
import { Dialog, ErrorNotice, Loading, SectionHeading } from "./ui";

export const preferenceLabels: Record<string, string> = {
  response_style: "回答风格",
  language: "交流语言",
  diet_preference: "饮食偏好",
  exercise_preference: "运动偏好",
  concise: "简洁明了",
  detailed: "详细解释",
  zh: "中文",
  en: "英文",
  light: "清淡饮食",
  vegetarian: "素食",
  no_spicy: "不辣的食物",
  walking: "散步",
  running: "跑步",
  swimming: "游泳",
  cycling: "骑行",
  yoga: "瑜伽",
};
const preferenceInfo = [
  {
    key: "response_style",
    icon: MessageSquare,
    description: "让每次交流更贴合你的阅读习惯。",
  },
  {
    key: "language",
    icon: Globe2,
    description: "用你熟悉的语言整理健康信息。",
  },
  {
    key: "diet_preference",
    icon: Leaf,
    description: "在相关饮食问题中，考虑你的喜好。",
  },
  {
    key: "exercise_preference",
    icon: Footprints,
    description: "从你愿意坚持的活动开始。",
  },
];

export function Memory({
  token,
  session,
}: {
  token: string;
  session: Session;
}) {
  const resource = useResource<MemoryData>("/api/memory", token);
  const [editing, setEditing] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function save(remove = false) {
    if (!editing) return;
    setBusy(true);
    setError(null);
    controller.current = new AbortController();
    try {
      await requestJson(`/api/memory/${editing}`, token, {
        method: remove ? "DELETE" : "PUT",
        ...(remove ? {} : { body: JSON.stringify({ value: selected }) }),
        signal: controller.current.signal,
      });
      setNotice(
        remove ? "已忘记这项偏好。" : "偏好已保存，将在相关对话中使用。",
      );
      setEditing(null);
      resource.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="page-content">
      <SectionHeading
        eyebrow="PERSONAL CONTEXT"
        title="让每次对话，更懂你的习惯"
        description="由你决定记住什么，也可以随时修改或忘记。"
        action={
          <button
            className="icon-button"
            aria-label="刷新偏好"
            onClick={resource.reload}
          >
            <RefreshCw size={17} />
          </button>
        }
      />
      <div className="memory-intro">
        <span className="memory-art">
          <Leaf size={38} strokeWidth={1.2} />
        </span>
        <div>
          <h3>记住偏好，尊重变化。</h3>
          <p>
            告诉助手“请记住：我喜欢清淡饮食”，
            <br />
            或在下面直接设置。健康指标会单独保存在健康记录中。
          </p>
        </div>
        <span
          className={`status-badge ${session.memory_enabled ? "ready" : "neutral"}`}
        >
          {session.memory_enabled ? "对话记忆已开启" : "对话记忆已关闭"}
        </span>
      </div>
      {!session.memory_enabled && (
        <p className="field-hint">
          当前未启用自动记忆与注入。你仍然可以管理已有偏好。
        </p>
      )}
      {notice && (
        <div className="success-notice" role="status">
          <Check size={17} />
          {notice}
        </div>
      )}
      {resource.error && (
        <ErrorNotice message={resource.error} retry={resource.reload} />
      )}
      {resource.loading ? (
        <Loading />
      ) : (
        resource.data && (
          <div className="preference-grid">
            {preferenceInfo.map(({ key, icon: Icon, description }) => {
              const preference = resource.data?.preferences.find(
                (item) => item.key === key,
              );
              return (
                <button
                  className="preference-card"
                  key={key}
                  onClick={() => {
                    setEditing(key);
                    setSelected(
                      preference?.value ??
                        resource.data?.allowed_values[key]?.[0] ??
                        "",
                    );
                    setDeleting(false);
                    setError(null);
                  }}
                >
                  <span className="preference-icon">
                    <Icon size={22} strokeWidth={1.6} />
                  </span>
                  <h3>{preferenceLabels[key]}</h3>
                  <p>{description}</p>
                  <div className="preference-value">
                    <span className={preference ? "" : "muted"}>
                      {preference
                        ? (preferenceLabels[preference.value] ??
                          preference.value)
                        : "尚未设置"}
                    </span>
                    <ChevronRight size={16} />
                  </div>
                  {preference && (
                    <small>
                      更新于{" "}
                      {formatDate(preference.updated_at, session.timezone)}
                    </small>
                  )}
                </button>
              );
            })}
          </div>
        )
      )}
      <div className="quiet-note">
        <Sparkles size={17} />
        <p>
          这些偏好会延续到新的对话。身体指标、病史和报告原文不会被当作偏好记忆。
        </p>
      </div>
      {editing && (
        <Dialog
          title={
            deleting
              ? `忘记${preferenceLabels[editing]}`
              : `设置${preferenceLabels[editing]}`
          }
          onClose={() => {
            if (!busy) setEditing(null);
          }}
        >
          <div className="form-stack">
            {deleting ? (
              <p className="dialog-description">
                这项偏好将从长期记忆中移除，之后的对话不再自动使用它。已有对话内容和健康记录会保留。
              </p>
            ) : (
              <label>
                选择偏好
                <select
                  aria-label="选择偏好"
                  value={selected}
                  onChange={(event) => setSelected(event.target.value)}
                >
                  {resource.data?.allowed_values[editing]?.map((value) => (
                    <option key={value} value={value}>
                      {preferenceLabels[value] ?? value}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {error && <ErrorNotice message={error} />}
            <div className="dialog-actions">
              {!deleting &&
                resource.data?.preferences.some(
                  (item) => item.key === editing,
                ) && (
                  <button
                    className="text-button danger push-left"
                    onClick={() => setDeleting(true)}
                    disabled={busy}
                  >
                    <Trash2 size={16} />
                    忘记
                  </button>
                )}
              <button
                className="secondary-button"
                disabled={busy}
                onClick={() =>
                  deleting ? setDeleting(false) : setEditing(null)
                }
              >
                取消
              </button>
              <button
                className={deleting ? "danger-button" : "primary-button"}
                disabled={busy || !selected}
                onClick={() => {
                  void save(deleting);
                }}
              >
                {busy ? "正在保存…" : deleting ? "确认忘记" : "保存偏好"}
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </section>
  );
}
