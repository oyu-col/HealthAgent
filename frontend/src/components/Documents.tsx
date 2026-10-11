import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  Check,
  FilePlus2,
  FileText,
  LoaderCircle,
  RefreshCw,
  UploadCloud,
} from "lucide-react";
import { requestJson } from "../lib/api";
import { errorMessage, formatDate, useResource } from "../lib/hooks";
import type { HealthDocument, Session } from "../lib/types";
import { Dialog, EmptyState, ErrorNotice, Loading, SectionHeading } from "./ui";

export function Documents({
  token,
  session,
  onAsk,
}: {
  token: string;
  session: Session;
  onAsk: (text: string) => void;
}) {
  const resource = useResource<{ documents: HealthDocument[] }>(
    "/api/documents",
    token,
  );
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [textOpen, setTextOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function upload(files: FileList | File[]) {
    if (busy || !files.length) return;
    setError(null);
    setNotice(null);
    const file = files[0];
    if (!/\.(txt|md|pdf)$/i.test(file.name)) {
      setError("请选择 TXT、Markdown 或 PDF 文件。");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("文件需小于 2 MiB，请精简后重新上传。");
      return;
    }
    if (!file.size) {
      setError("文件内容为空。");
      return;
    }
    setBusy(true);
    controller.current = new AbortController();
    const body = new FormData();
    body.append("file", file);
    try {
      const document = await requestJson<HealthDocument>(
        "/api/documents/upload",
        token,
        { method: "POST", body, signal: controller.current.signal },
      );
      resource.reload();
      if (document.index_status !== "indexed")
        setError(
          `「${document.filename}」未能建立索引。${document.parse_status === "failed" ? "请确认文档含有可提取文字；当前不支持扫描图片或加密 PDF。" : "请稍后重新上传同一文件重试。"}`,
        );
      else setNotice(`「${document.filename}」已就绪，可以在对话中提问。`);
    } catch (cause) {
      if (!controller.current.signal.aborted) setError(errorMessage(cause));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  const documents = resource.data?.documents ?? [];
  return (
    <section className="page-content">
      <SectionHeading
        eyebrow="PERSONAL KNOWLEDGE"
        title="让资料成为有用的线索"
        description="将报告与健康笔记放在这里，在对话中回到原文。"
        action={
          <button
            className="secondary-button"
            onClick={() => setTextOpen(true)}
          >
            <FilePlus2 size={17} />
            新建笔记
          </button>
        }
      />
      <div
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void upload(event.dataTransfer.files);
        }}
      >
        <span className="upload-icon">
          {busy ? (
            <LoaderCircle className="spin" size={29} />
          ) : (
            <UploadCloud size={30} strokeWidth={1.5} />
          )}
        </span>
        <h3>{busy ? "正在解析并整理文档…" : "把健康资料，轻轻放在这里"}</h3>
        <p>拖入一个文件，或从设备中选择</p>
        <button
          className="primary-button"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {busy ? "正在上传…" : "选择文件"}
        </button>
        <span className="field-hint">
          TXT、Markdown、含文字的 PDF · 最大 2 MiB
        </span>
        <input
          ref={input}
          type="file"
          className="visually-hidden"
          accept=".txt,.md,.pdf"
          aria-label="选择健康文档"
          onChange={(event) => {
            if (event.target.files) void upload(event.target.files);
          }}
        />
      </div>
      {error && <ErrorNotice message={error} />}
      {notice && (
        <div className="success-notice" role="status">
          <Check size={17} />
          {notice}
        </div>
      )}
      <div className="section-toolbar">
        <h2>
          我的文档{" "}
          {resource.data && <span className="count">{documents.length}</span>}
        </h2>
        <button
          className="icon-button"
          aria-label="刷新文档"
          onClick={resource.reload}
        >
          <RefreshCw size={16} />
        </button>
      </div>
      {resource.error && (
        <ErrorNotice message={resource.error} retry={resource.reload} />
      )}
      {resource.loading ? (
        <Loading />
      ) : (
        !resource.error &&
        (documents.length === 0 ? (
          <EmptyState icon={FileText} title="你的资料库还是空的">
            上传一份报告，或写下第一篇健康笔记。
            <br />
            资料仅供当前用户检索使用。
          </EmptyState>
        ) : (
          <div className="document-list">
            {documents.map((doc) => (
              <article className="document-row" key={doc.id}>
                <span
                  className={`file-icon ${doc.document_type === "pdf" ? "pdf" : ""}`}
                >
                  <FileText size={23} strokeWidth={1.5} />
                  <small>{doc.document_type.toUpperCase()}</small>
                </span>
                <div className="row-main">
                  <h3 title={doc.filename}>{doc.filename}</h3>
                  <p>
                    {formatDate(doc.created_at, session.timezone)} · 私人资料
                  </p>
                  {doc.error_code && (
                    <p className="error-text">
                      {doc.parse_status === "failed"
                        ? "解析失败，请上传可提取文字的文件"
                        : "索引失败，重新上传同一文件可重试"}
                    </p>
                  )}
                </div>
                <span
                  className={`status-badge ${doc.index_status === "indexed" ? "ready" : "failed"}`}
                >
                  {doc.index_status === "indexed"
                    ? "可检索"
                    : doc.index_status === "pending"
                      ? "待处理"
                      : "未就绪"}
                </span>
                <button
                  className="icon-button"
                  aria-label={`询问文档 ${doc.filename}`}
                  title="在对话中询问"
                  disabled={doc.index_status !== "indexed"}
                  onClick={() =>
                    onAsk(
                      `请检索我的文档「${doc.filename}」，帮我整理主要信息并标注原文出处。`,
                    )
                  }
                >
                  <ArrowUpRight size={18} />
                </button>
              </article>
            ))}
          </div>
        ))
      )}
      {textOpen && (
        <NoteForm
          token={token}
          onClose={() => setTextOpen(false)}
          onSaved={(doc) => {
            setTextOpen(false);
            resource.reload();
            setNotice(null);
            setError(null);
            if (doc.index_status === "indexed")
              setNotice("笔记已保存并可检索。");
            else setError("笔记已保存，但索引未就绪，请稍后重试。");
          }}
        />
      )}
    </section>
  );
}

function NoteForm({
  token,
  onClose,
  onSaved,
}: {
  token: string;
  onClose: () => void;
  onSaved: (doc: HealthDocument) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    let filename = String(form.get("filename")).trim();
    if (!/\.(txt|md)$/i.test(filename)) filename += ".md";
    setBusy(true);
    setError(null);
    controller.current = new AbortController();
    try {
      const doc = await requestJson<HealthDocument>(
        "/api/documents/text",
        token,
        {
          method: "POST",
          body: JSON.stringify({ filename, text: form.get("text") }),
          signal: controller.current.signal,
        },
      );
      onSaved(doc);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      title="新建健康笔记"
      wide
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
        <label>
          笔记名称
          <input
            name="filename"
            required
            maxLength={180}
            placeholder="例如：十月健康观察"
          />
        </label>
        <label>
          内容
          <textarea
            name="text"
            required
            rows={9}
            maxLength={200000}
            placeholder="整理你想在以后回顾的健康资料或问题…"
          />
        </label>
        <p className="field-hint">
          笔记用于资料检索。体重等结构化指标请在「健康记录」中保存。
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
            {busy ? "正在保存…" : "保存笔记"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
