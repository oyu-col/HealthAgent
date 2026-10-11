import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Activity,
  ArrowUpRight,
  Footprints,
  HeartPulse,
  Moon,
  Plus,
  RefreshCw,
  Utensils,
  Weight,
} from "lucide-react";
import { requestJson } from "../lib/api";
import {
  errorMessage,
  formatDate,
  localDateTime,
  useResource,
} from "../lib/hooks";
import type {
  HealthRecord,
  RecordKind,
  Session,
  ToolResult,
} from "../lib/types";
import { Dialog, EmptyState, ErrorNotice, Loading, SectionHeading } from "./ui";

const metrics = {
  weight: { label: "体重", unit: "kg", icon: Weight },
  heart_rate: { label: "静息心率", unit: "bpm", icon: HeartPulse },
  sleep_duration: { label: "睡眠时长", unit: "hours", icon: Moon },
  steps: { label: "步数", unit: "count", icon: Footprints },
};
const kindLabels = {
  metric: "身体指标",
  diet: "饮食记录",
  exercise: "运动记录",
};
const mealLabels: Record<string, string> = {
  breakfast: "早餐",
  lunch: "午餐",
  dinner: "晚餐",
  snack: "加餐",
};
const units: Record<string, string> = {
  kg: "kg",
  bpm: "次/分钟",
  hours: "小时",
  count: "步",
};

export function Records({
  token,
  session,
}: {
  token: string;
  session: Session;
}) {
  const [kind, setKind] = useState<RecordKind>("metric");
  const [adding, setAdding] = useState(false);
  const [filter, setFilter] = useState("");
  const resource = useResource<
    ToolResult<{ records: HealthRecord[]; truncated: boolean }>
  >(
    `/api/records/${kind}?limit=100${kind === "metric" && filter ? `&metric_type=${filter}` : ""}`,
    token,
  );
  const records = resource.data?.data?.records ?? [];
  const resultError =
    resource.data && !resource.data.success
      ? resource.data.error_message
      : null;
  return (
    <section className="page-content">
      <SectionHeading
        eyebrow="HEALTH JOURNAL"
        title="每一天，都有迹可循"
        description="把身体的变化与生活的点滴，留在同一个地方。"
        action={
          <button className="primary-button" onClick={() => setAdding(true)}>
            <Plus size={17} />
            添加记录
          </button>
        }
      />
      <div className="record-overview">
        <div className="overview-art">
          <Activity size={33} strokeWidth={1.5} />
          <span>记录是了解自己的开始</span>
          <p>
            真实记录，逐渐看见变化。
            <br />
            无需一次做很多，从今天的一小步开始。
          </p>
        </div>
        <div className="overview-note">
          <span className="eyebrow">YOUR OWN PACE</span>
          <h3>保持观察，无需急于下结论。</h3>
          <p>
            这里保存你明确填写的数据，方便回看与交流。单次指标不能代替专业判断。
          </p>
        </div>
      </div>
      <div className="section-toolbar">
        <div className="tabs" aria-label="记录类型">
          {(Object.keys(kindLabels) as RecordKind[]).map((item) => (
            <button
              key={item}
              className={kind === item ? "active" : ""}
              onClick={() => setKind(item)}
              aria-pressed={kind === item}
            >
              {kindLabels[item]}
            </button>
          ))}
        </div>
        <div className="toolbar-actions">
          {kind === "metric" && (
            <select
              aria-label="筛选指标"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="">全部指标</option>
              {Object.entries(metrics).map(([value, item]) => (
                <option key={value} value={value}>
                  {item.label}
                </option>
              ))}
            </select>
          )}
          <button
            className="icon-button"
            aria-label="刷新记录"
            onClick={resource.reload}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>
      {(resource.error || resultError) && (
        <ErrorNotice
          message={resource.error || resultError || "加载失败"}
          retry={resource.reload}
        />
      )}
      {resource.loading ? (
        <Loading />
      ) : (
        !resource.error &&
        !resultError &&
        (records.length === 0 ? (
          <EmptyState
            icon={
              kind === "diet"
                ? Utensils
                : kind === "exercise"
                  ? Footprints
                  : Activity
            }
            title="从第一条记录开始"
            action={
              <button className="text-button" onClick={() => setAdding(true)}>
                添加{kindLabels[kind]} <ArrowUpRight size={16} />
              </button>
            }
          >
            这里会显示你保存的{kindLabels[kind]}，<br />
            包括时间与每一项具体数值。
          </EmptyState>
        ) : (
          <div className="record-list">
            {records.map((record) => {
              const metric = record.metric_type
                ? metrics[record.metric_type]
                : null;
              const Icon =
                metric?.icon ?? (kind === "diet" ? Utensils : Footprints);
              return (
                <article className="record-row" key={record.id}>
                  <span className="row-icon">
                    <Icon size={20} />
                  </span>
                  <div className="row-main">
                    <h3>
                      {metric?.label ??
                        record.food_name ??
                        record.exercise_type}
                    </h3>
                    <p>
                      {record.measured_at || record.timestamp
                        ? formatDate(
                            (record.measured_at ?? record.timestamp)!,
                            session.timezone,
                          )
                        : "时间未提供"}
                      {record.meal_type && ` · ${mealLabels[record.meal_type]}`}
                    </p>
                  </div>
                  <div className="record-value">
                    {kind === "metric" ? (
                      <>
                        {record.value}
                        <small>{units[record.unit ?? ""] ?? record.unit}</small>
                      </>
                    ) : kind === "diet" ? (
                      <>{record.amount}</>
                    ) : (
                      <>
                        {record.duration}
                        <small>
                          分钟
                          {record.distance != null &&
                            ` · ${record.distance} km`}
                        </small>
                      </>
                    )}
                  </div>
                </article>
              );
            })}
            {resource.data?.data?.truncated && (
              <p className="muted list-note">
                当前显示最近 100 条记录；可通过对话按时间范围查询。
              </p>
            )}
          </div>
        ))
      )}
      {adding && (
        <RecordForm
          kind={kind}
          token={token}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            resource.reload();
          }}
        />
      )}
    </section>
  );
}

function RecordForm({
  kind,
  token,
  onClose,
  onSaved,
}: {
  kind: RecordKind;
  token: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [metricType, setMetricType] = useState<keyof typeof metrics>("weight");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const operation = useRef<{ payload: string; id: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const time = new Date(String(form.get("time"))).toISOString();
    let record: Record<string, unknown>;
    if (kind === "metric")
      record = {
        metric_type: metricType,
        value: Number(form.get("value")),
        unit: metrics[metricType].unit,
        measured_at: time,
      };
    else if (kind === "diet")
      record = {
        food_name: String(form.get("food")),
        amount: String(form.get("amount")),
        meal_type: String(form.get("meal")),
        timestamp: time,
      };
    else
      record = {
        exercise_type: String(form.get("exercise")),
        duration: Number(form.get("duration")),
        timestamp: time,
        distance: form.get("distance") ? Number(form.get("distance")) : null,
      };
    const payload = JSON.stringify(record);
    if (!operation.current || operation.current.payload !== payload)
      operation.current = { payload, id: crypto.randomUUID() };
    setBusy(true);
    setError(null);
    controller.current = new AbortController();
    try {
      const response = await requestJson<ToolResult<HealthRecord>>(
        `/api/records/${kind}`,
        token,
        {
          method: "POST",
          body: JSON.stringify({ record, request_id: operation.current.id }),
          signal: controller.current.signal,
        },
      );
      if (!response.success)
        throw new Error(response.error_message ?? "记录未保存");
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      title={`添加${kindLabels[kind]}`}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form
        className="form-stack"
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        {kind === "metric" && (
          <>
            <label>
              指标
              <select
                value={metricType}
                onChange={(event) =>
                  setMetricType(event.target.value as keyof typeof metrics)
                }
              >
                {Object.entries(metrics).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              数值（{units[metrics[metricType].unit]}）
              <input
                name="value"
                type="number"
                required
                min={
                  metricType === "weight" || metricType === "heart_rate"
                    ? "0.01"
                    : "0"
                }
                max={metricType === "sleep_duration" ? "24" : undefined}
                step={metricType === "steps" ? "1" : "any"}
                placeholder="填写实际测量值"
              />
            </label>
          </>
        )}
        {kind === "diet" && (
          <>
            <label>
              食物
              <input
                name="food"
                required
                maxLength={200}
                placeholder="例如：燕麦、牛奶"
              />
            </label>
            <div className="form-grid">
              <label>
                份量
                <input
                  name="amount"
                  required
                  maxLength={200}
                  placeholder="例如：50 g"
                />
              </label>
              <label>
                餐次
                <select name="meal">
                  {Object.entries(mealLabels).map(([key, value]) => (
                    <option key={key} value={key}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </>
        )}
        {kind === "exercise" && (
          <>
            <label>
              运动项目
              <input
                name="exercise"
                required
                maxLength={200}
                placeholder="例如：散步"
              />
            </label>
            <div className="form-grid">
              <label>
                时长（分钟）
                <input
                  name="duration"
                  type="number"
                  min="0.1"
                  max="1440"
                  step="any"
                  required
                />
              </label>
              <label>
                距离（km，可选）
                <input name="distance" type="number" min="0" step="any" />
              </label>
            </div>
          </>
        )}
        <label>
          记录时间
          <input
            type="datetime-local"
            name="time"
            required
            defaultValue={localDateTime()}
          />
        </label>
        <p className="field-hint">
          使用当前设备时区；保存后将按工作空间时区显示。
        </p>
        {error && <ErrorNotice message={error} />}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={onClose}
          >
            取消
          </button>
          <button className="primary-button" disabled={busy}>
            {busy ? "正在保存…" : "保存记录"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
