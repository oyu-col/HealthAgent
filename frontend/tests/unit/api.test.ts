import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestJson, streamChat } from "../../src/lib/api";
import type { ChatInput, StreamEvent } from "../../src/lib/types";

const input: ChatInput = { message: "合成问题", request_id: "request-1" };
const identity = {
  version: 1,
  trace_id: "trace-1",
  run_id: "run-1",
  thread_id: "thread-1",
  request_id: "request-1",
};
const started = { ...identity, seq: 1, model_mode: "fake" };
const completed = {
  ...identity,
  seq: 3,
  answer: "最终的中文回答",
  model_mode: "fake",
  termination_reason: "completed",
  memory_updates: [],
};
const encoder = new TextEncoder();

function frame(
  event: string,
  data: Record<string, unknown>,
  newline = "\n",
): string {
  return `event: ${event}${newline}data: ${JSON.stringify(data)}${newline}${newline}`;
}

function mockStream(bytes: Uint8Array[], close = true) {
  const cancel = vi.fn();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of bytes) controller.enqueue(chunk);
      if (close) controller.close();
    },
    cancel,
  });
  const response = new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "X-Trace-ID": "trace-1",
    },
  });
  const fetch = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetch);
  return { cancel, stream, fetch };
}

function mockJson(body: unknown, status = 200) {
  const fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: {
        "Content-Type": "application/json",
        "X-Trace-ID": "trace-1",
      },
    }),
  );
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

afterEach(() => vi.unstubAllGlobals());

describe("JSON API requests", () => {
  it("uses a same-origin URL, JSON headers and in-memory bearer", async () => {
    const fetch = mockJson({ success: true });
    expect(
      await requestJson("/api/health/metrics?limit=10", " example-token ", {
        method: "POST",
        body: JSON.stringify({ value: 60 }),
      }),
    ).toEqual({ success: true });
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/health/metrics?limit=10");
    expect(options.headers.get("Authorization")).toBe("Bearer example-token");
    expect(options.headers.get("Content-Type")).toBe("application/json");
    expect(options.redirect).toBe("error");
    expect(options.cache).toBe("no-store");
  });

  it("does not retain a caller authorization header when token is empty", async () => {
    const fetch = mockJson({ status: "ok" });
    await requestJson("/healthz", "", {
      headers: { Authorization: "Bearer stale-user" },
    });
    expect(fetch.mock.calls[0][1].headers.has("Authorization")).toBe(false);
  });

  it("lets fetch set the multipart boundary", async () => {
    const fetch = mockJson({ id: "document-1" });
    const body = new FormData();
    body.append(
      "file",
      new Blob(["合成文本"], { type: "text/plain" }),
      "test.txt",
    );
    await requestJson("/api/documents", "", {
      method: "POST",
      body,
      headers: { "Content-Type": "application/json" },
    });
    expect(fetch.mock.calls[0][1].body).toBe(body);
    expect(fetch.mock.calls[0][1].headers.has("Content-Type")).toBe(false);
  });

  it.each([
    "https://outside.invalid/api",
    "//outside.invalid/api",
    "/api/../../outside",
    "/api\\outside",
    "/other",
    "api/test",
  ])("rejects a non-API path %s before fetch", async (path) => {
    const fetch = mockJson({});
    await expect(requestJson(path, "secret")).rejects.toMatchObject({
      code: "invalid_api_path",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("preserves the backend safe error and recovery identifiers", async () => {
    mockJson(
      {
        error: {
          code: "thread_busy",
          message: "会话正在运行。",
          trace_id: "trace-2",
          thread_id: "thread-9",
          request_id: "request-7",
        },
      },
      409,
    );
    await expect(requestJson("/api/chat", "")).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      code: "thread_busy",
      message: "会话正在运行。",
      traceId: "trace-2",
      threadId: "thread-9",
      requestId: "request-7",
    });
  });

  it("does not show HTML error pages to the user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html>PRIVATE proxy configuration</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );
    await expect(requestJson("/api/session", "")).rejects.toMatchObject({
      status: 502,
      code: "http_502",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html>proxy</html>", {
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );
    await expect(requestJson("/api/session", "")).rejects.toMatchObject({
      code: "invalid_response",
    });
  });

  it("reports malformed JSON and unavailable connections safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("{broken", {
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(requestJson("/api/session", "")).rejects.toMatchObject({
      code: "invalid_response",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("PRIVATE network internals")),
    );
    await expect(requestJson("/api/session", "")).rejects.toMatchObject({
      code: "network_error",
      message: "无法连接健康助手服务，请检查网络和后端运行状态。",
    });
  });

  it("supports bodyless successful deletion", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    expect(
      await requestJson("/api/memory/example", "", { method: "DELETE" }),
    ).toBeUndefined();
  });
});

describe("incremental SSE chat", () => {
  it("decodes split UTF-8, CRLF, comments, multiline data and authoritative completion", async () => {
    const text =
      ": heartbeat\r\n\r\n" +
      frame("run.started", started, "\r\n") +
      `event: message.delta\r\ndata: ${JSON.stringify({ ...identity, seq: 2, text: "部分中文" }).slice(0, -1)}\r\ndata: }\r\n\r\n` +
      frame("run.completed", completed, "\r\n");
    const bytes = encoder.encode(text);
    const { fetch, stream } = mockStream(
      [...bytes].map((byte) => new Uint8Array([byte])),
    );
    const events: StreamEvent[] = [];
    const result = await streamChat(
      input,
      "token",
      (event) => events.push(event),
      new AbortController().signal,
    );
    expect(events.map((event) => event.event)).toEqual([
      "run.started",
      "message.delta",
      "run.completed",
    ]);
    expect(events[1].data.text).toBe("部分中文");
    expect(result.answer).toBe("最终的中文回答");
    expect(result.answer).not.toBe(events[1].data.text);
    expect(fetch.mock.calls[0][0]).toBe("/api/chat/stream");
    expect(fetch.mock.calls[0][1].headers.get("Accept")).toBe(
      "text/event-stream",
    );
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
    expect(stream.locked).toBe(false);
  });

  it("delivers several frames from one network chunk and closes an open transport on completion", async () => {
    const text =
      frame("run.started", started) +
      frame("tool.started", {
        ...identity,
        seq: 2,
        name: "query_health_metrics",
        tool_call_id: "call-1",
      }) +
      frame("tool.finished", {
        ...identity,
        seq: 3,
        name: "query_health_metrics",
        tool_call_id: "call-1",
        success: true,
        error_code: null,
      }) +
      frame("run.completed", { ...completed, seq: 4 });
    const { cancel, stream } = mockStream([encoder.encode(text)], false);
    const events: StreamEvent[] = [];
    await streamChat(
      input,
      "",
      (event) => events.push(event),
      new AbortController().signal,
    );
    expect(events.map((event) => event.event)).toEqual([
      "run.started",
      "tool.started",
      "tool.finished",
      "run.completed",
    ]);
    expect(cancel).toHaveBeenCalledOnce();
    expect(stream.locked).toBe(false);
  });

  it("rejects a clean EOF without completion and retains recovery identifiers", async () => {
    mockStream([
      encoder.encode(
        frame("run.started", started) +
          frame("message.delta", { ...identity, seq: 2, text: "不完整" }),
      ),
    ]);
    await expect(
      streamChat(input, "", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({
      code: "stream_incomplete",
      threadId: "thread-1",
      requestId: "request-1",
      traceId: "trace-1",
    });
  });

  it("does not commit a final frame missing its blank separator", async () => {
    mockStream([
      encoder.encode(
        frame("run.started", started) +
          frame("run.completed", { ...completed, seq: 2 }).trimEnd(),
      ),
    ]);
    await expect(
      streamChat(input, "", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({ code: "stream_incomplete" });
  });

  it("surfaces a terminal server failure with its safe message", async () => {
    mockStream([
      encoder.encode(
        frame("run.started", started) +
          frame("run.failed", {
            ...identity,
            seq: 2,
            error_code: "request_timeout",
            error_message: "请求超时，请恢复。",
          }),
      ),
    ]);
    const receive = vi.fn();
    await expect(
      streamChat(input, "", receive, new AbortController().signal),
    ).rejects.toMatchObject({
      code: "request_timeout",
      message: "请求超时，请恢复。",
      threadId: "thread-1",
    });
    expect(receive.mock.calls.at(-1)?.[0].event).toBe("run.failed");
  });

  it("accepts a prepare-stage failure before run.started", async () => {
    mockStream([
      encoder.encode(
        frame("run.failed", {
          version: 1,
          trace_id: "trace-1",
          run_id: null,
          thread_id: null,
          seq: 1,
          error_code: "storage_unavailable",
          error_message: "存储暂时不可用。",
        }),
      ),
    ]);
    await expect(
      streamChat(input, "", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({
      code: "storage_unavailable",
      requestId: "request-1",
    });
  });

  it.each([
    { seq: 1 },
    { seq: 3 },
    { version: 2 },
    { trace_id: "other-trace" },
    { thread_id: "other-thread" },
    { request_id: "other-request" },
    { run_id: "other-run" },
    { text: { hidden: "not text" } },
  ])(
    "rejects contaminated or out-of-order frame %j before callback",
    async (changed) => {
      mockStream([
        encoder.encode(
          frame("run.started", started) +
            frame("message.delta", {
              ...identity,
              seq: 2,
              text: "中文",
              ...changed,
            }),
        ),
      ]);
      const receive = vi.fn();
      await expect(
        streamChat(input, "", receive, new AbortController().signal),
      ).rejects.toMatchObject({ code: "invalid_stream", threadId: "thread-1" });
      expect(receive).toHaveBeenCalledTimes(1);
    },
  );

  it("rejects malformed JSON and oversized frames without exposing raw content", async () => {
    mockStream([
      encoder.encode("event: run.started\ndata: {PRIVATE invalid\n\n"),
    ]);
    await expect(
      streamChat(input, "", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({ code: "invalid_stream" });
    const { cancel } = mockStream(
      [encoder.encode("data: " + "x".repeat(1024 * 1024 + 1))],
      false,
    );
    await expect(
      streamChat(input, "", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({ code: "invalid_stream" });
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("handles an unauthorized HTTP response before opening a stream", async () => {
    mockJson(
      {
        error: {
          code: "unauthorized",
          message: "访问凭据无效。",
          trace_id: "trace-1",
        },
      },
      401,
    );
    await expect(
      streamChat(input, "bad-token", () => {}, new AbortController().signal),
    ).rejects.toMatchObject({
      status: 401,
      code: "unauthorized",
      requestId: "request-1",
    });
  });

  it("cancels a pending reader and releases its lock when aborted", async () => {
    const controller = new AbortController();
    const { cancel, stream } = mockStream(
      [encoder.encode(frame("run.started", started))],
      false,
    );
    const received = vi.fn();
    const pending = streamChat(input, "", received, controller.signal);
    await vi.waitFor(() => expect(received).toHaveBeenCalledOnce());
    const assertion = expect(pending).rejects.toMatchObject({
      name: "AbortError",
    });
    controller.abort();
    await assertion;
    expect(cancel).toHaveBeenCalledOnce();
    expect(stream.locked).toBe(false);
  });

  it("never fetches when already aborted", async () => {
    const fetch = mockJson({});
    const controller = new AbortController();
    controller.abort();
    await expect(
      streamChat(input, "", () => {}, controller.signal),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("keeps caller recovery IDs if connection fails before response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("synthetic offline")),
    );
    await expect(
      streamChat(
        { ...input, thread_id: "known-thread" },
        "",
        () => {},
        new AbortController().signal,
      ),
    ).rejects.toMatchObject({
      code: "network_error",
      threadId: "known-thread",
      requestId: "request-1",
    });
  });

  it("exports an ordinary Error carrying application metadata", () => {
    const error = new ApiError("synthetic", 503, "temporary", {
      traceId: "trace",
    });
    expect(error).toBeInstanceOf(Error);
    expect(error.traceId).toBe("trace");
  });
});
