import type { ChatInput, ChatResult, StreamEvent } from "./types";

type Recovery = { traceId?: string; threadId?: string; requestId?: string };

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly traceId?: string;
  readonly threadId?: string;
  readonly requestId?: string;

  constructor(
    message: string,
    status = 0,
    code = "network_error",
    recovery: Recovery = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.traceId = recovery.traceId;
    this.threadId = recovery.threadId;
    this.requestId = recovery.requestId;
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function identifier(value: unknown): value is string {
  return typeof value === "string" && /^[a-zA-Z0-9_-]{1,128}$/.test(value);
}

function checkAbort(signal?: AbortSignal | null): void {
  if (signal?.aborted) throw new DOMException("请求已取消。", "AbortError");
}

function isAbort(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

function localPath(path: string): string {
  const base = "https://health-agent.invalid";
  const url = new URL(path, base);
  if (
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path.includes("\\") ||
    url.origin !== base ||
    url.hash ||
    !(
      url.pathname === "/healthz" ||
      url.pathname === "/api" ||
      url.pathname.startsWith("/api/")
    )
  ) {
    throw new ApiError(
      "请求地址必须是本站的健康助手接口。",
      0,
      "invalid_api_path",
    );
  }
  return url.pathname + url.search;
}

async function fetchApi(
  path: string,
  token: string,
  options: RequestInit,
): Promise<Response> {
  const target = localPath(path);
  const headers = new Headers(options.headers);
  headers.delete("Authorization");
  if (token.trim()) headers.set("Authorization", `Bearer ${token.trim()}`);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (options.body instanceof FormData) headers.delete("Content-Type");
  else if (typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  checkAbort(options.signal);
  try {
    return await fetch(target, {
      ...options,
      headers,
      credentials: "same-origin",
      redirect: "error",
      cache: "no-store",
    });
  } catch (error) {
    checkAbort(options.signal);
    if (isAbort(error)) throw error;
    throw new ApiError(
      "无法连接健康助手服务，请检查网络和后端运行状态。",
      0,
      "network_error",
    );
  }
}

function jsonContent(response: Response): boolean {
  return /\bapplication\/(?:[a-z0-9.+-]+\+)?json\b/i.test(
    response.headers.get("Content-Type") ?? "",
  );
}

async function responseError(
  response: Response,
  fallback: Recovery = {},
): Promise<ApiError> {
  const recovery = { ...fallback };
  const trace = response.headers.get("X-Trace-ID");
  if (identifier(trace)) recovery.traceId = trace;
  let body: unknown;
  if (jsonContent(response)) {
    try {
      body = await response.json();
    } catch {
      // Never show a proxy's HTML or a partial response as an application error.
    }
  }
  if (record(body) && record(body.error)) {
    const error = body.error;
    if (identifier(error.trace_id)) recovery.traceId = error.trace_id;
    if (identifier(error.thread_id)) recovery.threadId = error.thread_id;
    if (identifier(error.request_id)) recovery.requestId = error.request_id;
    if (typeof error.message === "string" && typeof error.code === "string") {
      return new ApiError(
        error.message.slice(0, 2000),
        response.status,
        error.code,
        recovery,
      );
    }
  }
  return new ApiError(
    response.status === 401
      ? "访问凭据无效或已失效，请重新连接。"
      : `服务请求失败（HTTP ${response.status}），请稍后重试。`,
    response.status,
    `http_${response.status}`,
    recovery,
  );
}

export async function requestJson<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetchApi(path, token, options);
  if (!response.ok) throw await responseError(response);
  if (response.status === 204) return undefined as T;
  if (!jsonContent(response)) {
    throw new ApiError(
      "服务返回了非 JSON 内容，请检查 API 代理配置。",
      response.status,
      "invalid_response",
    );
  }
  try {
    const result: unknown = await response.json();
    checkAbort(options.signal);
    return result as T;
  } catch (error) {
    checkAbort(options.signal);
    if (isAbort(error)) throw error;
    throw new ApiError(
      "服务返回的数据不完整，请重试。",
      response.status,
      "invalid_response",
    );
  }
}

const MAX_FRAME_CHARS = 1024 * 1024;
const EVENT_NAMES = new Set([
  "run.started",
  "message.delta",
  "tool.started",
  "tool.finished",
  "run.completed",
  "run.failed",
]);

/** A small SSE line decoder; UTF-8 decoding stays incremental in streamChat. */
class EventDecoder {
  private buffer = "";
  private event = "";
  private data: string[] = [];
  private frameSize = 0;

  feed(
    text: string,
    receive: (event: string, data: string) => boolean,
  ): boolean {
    this.buffer += text;
    let start = 0;
    for (let index = 0; index < this.buffer.length; index++) {
      const character = this.buffer[index];
      if (character !== "\r" && character !== "\n") continue;
      // Preserve a chunk-ending CR until its possible LF arrives.
      if (character === "\r" && index === this.buffer.length - 1) break;
      const line = this.buffer.slice(start, index);
      if (character === "\r" && this.buffer[index + 1] === "\n") index++;
      start = index + 1;
      this.frameSize += line.length + 1;
      if (this.frameSize > MAX_FRAME_CHARS)
        throw new Error("oversized SSE frame");
      if (line === "") {
        const event = this.event;
        const data = this.data.join("\n");
        this.event = "";
        this.data = [];
        this.frameSize = 0;
        if (data && receive(event, data)) return true;
      } else if (!line.startsWith(":")) {
        const separator = line.indexOf(":");
        const field = separator < 0 ? line : line.slice(0, separator);
        let value = separator < 0 ? "" : line.slice(separator + 1);
        if (value.startsWith(" ")) value = value.slice(1);
        if (field === "event") this.event = value;
        if (field === "data") this.data.push(value);
      }
    }
    this.buffer = this.buffer.slice(start);
    if (this.frameSize + this.buffer.length > MAX_FRAME_CHARS) {
      throw new Error("oversized SSE frame");
    }
    return false;
  }
}

export async function streamChat(
  body: ChatInput,
  token: string,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<ChatResult> {
  const recovery: Recovery = {
    threadId: body.thread_id,
    requestId: body.request_id,
  };
  let response: Response;
  try {
    response = await fetchApi("/api/chat/stream", token, {
      method: "POST",
      headers: { Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw new ApiError(error.message, error.status, error.code, recovery);
    }
    throw error;
  }
  if (!response.ok) throw await responseError(response, recovery);
  const trace = response.headers.get("X-Trace-ID");
  if (identifier(trace)) recovery.traceId = trace;
  if (
    !response.headers
      .get("Content-Type")
      ?.toLowerCase()
      .startsWith("text/event-stream") ||
    !response.body
  ) {
    throw new ApiError(
      "服务没有返回事件流，请检查 API 代理配置。",
      response.status,
      "invalid_stream",
      recovery,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const frames = new EventDecoder();
  let expectedSequence = 1;
  let runId: string | undefined;
  let started = false;
  let modelMode: "fake" | "provider" | undefined;
  let result: ChatResult | undefined;

  function invalid(): never {
    throw new ApiError(
      "事件流格式异常，已停止接收。请检查会话状态后恢复。",
      0,
      "invalid_stream",
      recovery,
    );
  }

  function receive(name: string, raw: string): boolean {
    if (!EVENT_NAMES.has(name)) invalid();
    let data: unknown;
    try {
      data = JSON.parse(raw);
    } catch {
      invalid();
    }
    if (
      !record(data) ||
      data.version !== 1 ||
      data.seq !== expectedSequence ||
      !identifier(data.trace_id) ||
      (recovery.traceId !== undefined && data.trace_id !== recovery.traceId) ||
      (data.thread_id !== null && !identifier(data.thread_id)) ||
      (data.run_id !== null && !identifier(data.run_id)) ||
      (data.request_id !== undefined && !identifier(data.request_id)) ||
      (data.request_id !== undefined &&
        data.request_id !== recovery.requestId) ||
      (recovery.threadId !== undefined &&
        data.thread_id !== recovery.threadId) ||
      (runId !== undefined && data.run_id !== runId)
    )
      invalid();
    if (!started && name !== "run.started" && name !== "run.failed") invalid();
    if (
      started &&
      (data.request_id !== recovery.requestId ||
        data.thread_id === null ||
        data.run_id === null)
    )
      invalid();

    if (name === "run.started") {
      if (
        started ||
        !identifier(data.run_id) ||
        !identifier(data.thread_id) ||
        !identifier(data.request_id)
      )
        invalid();
      if (data.model_mode !== "fake" && data.model_mode !== "provider")
        invalid();
      started = true;
      runId = data.run_id;
      modelMode = data.model_mode;
    }
    if (name === "message.delta" && typeof data.text !== "string") invalid();
    if (name.startsWith("tool.")) {
      if (typeof data.name !== "string" || !identifier(data.tool_call_id))
        invalid();
      if (name === "tool.finished" && typeof data.success !== "boolean")
        invalid();
    }
    if (
      name === "run.failed" &&
      (typeof data.error_code !== "string" ||
        typeof data.error_message !== "string")
    )
      invalid();
    if (name === "run.completed") {
      if (
        typeof data.answer !== "string" ||
        !data.answer.trim() ||
        data.termination_reason !== "completed" ||
        data.model_mode !== modelMode ||
        !Array.isArray(data.memory_updates) ||
        !data.memory_updates.every(
          (item) =>
            record(item) &&
            typeof item.key === "string" &&
            (typeof item.value === "string" || item.value === null),
        )
      )
        invalid();
      result = data as ChatResult;
    }
    recovery.traceId = data.trace_id;
    if (identifier(data.thread_id)) recovery.threadId = data.thread_id;
    expectedSequence++;
    onEvent({ event: name, data } as StreamEvent);
    if (name === "run.failed") {
      throw new ApiError(
        String(data.error_message).slice(0, 2000),
        200,
        String(data.error_code),
        recovery,
      );
    }
    return result !== undefined;
  }

  const cancel = () => {
    void reader.cancel().catch(() => undefined);
  };
  signal.addEventListener("abort", cancel, { once: true });
  try {
    while (true) {
      checkAbort(signal);
      const chunk = await reader.read();
      checkAbort(signal);
      if (chunk.done) {
        // A complete SSE frame requires its blank separator; EOF cannot commit it.
        frames.feed(decoder.decode(), receive);
        throw new ApiError(
          "连接已中断，尚未收到完整回答。请检查会话状态后恢复。",
          0,
          "stream_incomplete",
          recovery,
        );
      }
      if (frames.feed(decoder.decode(chunk.value, { stream: true }), receive)) {
        checkAbort(signal);
        return result!;
      }
    }
  } catch (error) {
    checkAbort(signal);
    if (error instanceof ApiError || isAbort(error)) throw error;
    throw new ApiError(
      "事件流读取失败，请检查会话状态后恢复。",
      0,
      "invalid_stream",
      recovery,
    );
  } finally {
    signal.removeEventListener("abort", cancel);
    try {
      await reader.cancel();
    } catch {
      /* A broken transport may already be closed. */
    }
    reader.releaseLock();
  }
}
