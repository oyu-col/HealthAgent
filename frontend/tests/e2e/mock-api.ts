import type { Page, Route } from "@playwright/test";
import type {
  ChatInput,
  ChatResult,
  HealthDocument,
  HealthRecord,
  MemoryData,
  ThreadState,
} from "../../src/lib/types";

export const ALICE_TOKEN = "synthetic-alice-token-123";
export const BOB_TOKEN = "synthetic-bob-token-456";
export const HISTORIC_THREAD = "00000000-0000-4000-8000-000000000001";
export const ANSWER = "已整理这次的观察。先保留记录，再看看一周的变化。";
const DATE = "2026-10-03T08:00:00+08:00";
export const TRACE = "synthetic-trace-1";
const RUN = "00000000-0000-4000-8000-000000000010";
const UUID = (value: number) =>
  `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;

export type SeenRequest = {
  path: string;
  method: string;
  body: unknown;
  authorization?: string;
};
type OwnerData = {
  threads: ThreadState[];
  records: Record<string, HealthRecord[]>;
  documents: HealthDocument[];
  memory: MemoryData;
};

function ownerData(owner: string): OwnerData {
  return {
    threads: [
      {
        thread_id: owner === "alice" ? HISTORIC_THREAD : UUID(2),
        title:
          owner === "alice"
            ? "合成用户 Alice 的健康观察"
            : "合成用户 Bob 的独立会话",
        created_at: DATE,
        active_request_id: null,
        status: "completed",
        pending: false,
        can_resume: false,
        messages: [
          {
            role: "user",
            content:
              owner === "alice"
                ? "这是 Alice 的历史问题"
                : "这是 Bob 的历史问题",
          },
          {
            role: "assistant",
            content:
              owner === "alice"
                ? "这是 Alice 的历史回答"
                : "这是 Bob 的历史回答",
          },
        ],
      },
    ],
    records: { metric: [], diet: [], exercise: [] },
    documents: [],
    memory: {
      preferences: [],
      allowed_values: {
        response_style: ["concise", "detailed"],
        language: ["zh", "en"],
        diet_preference: ["light", "vegetarian", "no_spicy"],
        exercise_preference: [
          "walking",
          "running",
          "swimming",
          "cycling",
          "yoga",
        ],
      },
    },
  };
}

/** Synthetic data only; every API request is intercepted before reaching Vite's proxy. */
export class MockApi {
  readonly requests: SeenRequest[] = [];
  readonly unexpected: string[] = [];
  readonly owners = { alice: ownerData("alice"), bob: ownerData("bob") };
  requireAuth = false;
  streamMode: "complete" | "incomplete" = "complete";
  ingestionStatus: "indexed" | "failed" = "indexed";
  readonly trace = {
    trace_id: TRACE,
    status: "interrupted",
    termination_reason: null,
    latency_ms: null,
    model_calls: null,
    tool_calls: null,
    subagent_calls: null,
    retry_count: null,
    total_steps: null,
    task_kind: "resume",
    capture_complete: false,
    dropped_events: 2,
    token_usage: {
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
      complete: false,
    },
    events: [
      { seq: 1, event: "run.started", elapsed_ms: 0 },
      { seq: 2, event: "model.finished", elapsed_ms: 17, success: true },
      {
        seq: 3,
        event: "tool.finished",
        name: "query_health_metrics",
        elapsed_ms: 31,
        success: false,
        error_code: null,
      },
    ],
  };
  private nextId = 100;

  async install(page: Page) {
    await page.route("**/api/**", (route) => this.handle(route));
    await page.route("**/healthz", (route) =>
      this.json(route, { status: "ok", phase: 12, model_mode: "fake" }),
    );
  }

  private json(route: Route, value: unknown, status = 200) {
    return route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  }

  private async handle(route: Route) {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    const authorization = request.headers().authorization;
    let body: unknown = null;
    if (request.headers()["content-type"]?.includes("application/json"))
      body = request.postDataJSON();
    this.requests.push({ path, method, body, authorization });
    const authenticated = [ALICE_TOKEN, BOB_TOKEN].some(
      (token) => authorization === `Bearer ${token}`,
    );
    if (this.requireAuth && !authenticated) {
      return this.json(
        route,
        {
          error: {
            code: "unauthorized",
            message: "访问凭据无效或已失效，请重新连接。",
            trace_id: TRACE,
          },
        },
        401,
      );
    }
    const owner = authorization === `Bearer ${BOB_TOKEN}` ? "bob" : "alice";
    const data = this.owners[owner];
    if (path === `/api/traces/${TRACE}` && method === "GET")
      return this.json(route, this.trace);
    if (path === "/api/session" && method === "GET") {
      return this.json(route, {
        user_id: owner,
        model_mode: "fake",
        timezone: "Asia/Shanghai",
        memory_enabled: true,
      });
    }
    if (path === "/api/threads" && method === "GET")
      return this.json(route, { threads: data.threads });
    if (path === "/api/threads" && method === "POST") {
      const thread = this.createThread(data);
      return this.json(route, thread);
    }
    if (/^\/api\/threads\/[^/]+$/.test(path) && method === "GET") {
      const thread = data.threads.find(
        (item) => item.thread_id === path.split("/")[3],
      );
      return this.json(
        route,
        thread ?? { error: { code: "not_found", message: "会话不存在" } },
        thread ? 200 : 404,
      );
    }
    if (path === "/api/chat/stream" && method === "POST") {
      const input = body as ChatInput;
      const thread =
        data.threads.find((item) => item.thread_id === input.thread_id) ??
        this.createThread(data);
      thread.title = input.message;
      thread.messages.push({ role: "user", content: input.message });
      thread.active_request_id =
        this.streamMode === "incomplete" ? input.request_id : null;
      thread.pending = this.streamMode === "incomplete";
      thread.can_resume = thread.pending;
      thread.status = thread.pending ? "interrupted" : "completed";
      if (!thread.pending)
        thread.messages.push({ role: "assistant", content: ANSWER });
      const common = {
        version: 1,
        trace_id: TRACE,
        run_id: RUN,
        thread_id: thread.thread_id,
        request_id: input.request_id,
      };
      const events: [string, Record<string, unknown>][] = [
        ["run.started", { model_mode: "fake" }],
        ["message.delta", { text: "已整理这次" }],
        ["message.delta", { text: "的观察。" }],
      ];
      if (this.streamMode === "complete")
        events.push([
          "run.completed",
          this.result(thread.thread_id, input.request_id),
        ]);
      return route.fulfill({
        status: 200,
        contentType: "text/event-stream; charset=utf-8",
        headers: { "X-Trace-ID": TRACE, "Cache-Control": "no-store" },
        body: events
          .map(
            ([name, extra], index) =>
              `event: ${name}\ndata: ${JSON.stringify({ ...common, seq: index + 1, ...extra })}\n\n`,
          )
          .join(""),
      });
    }
    if (/^\/api\/threads\/[^/]+\/resume$/.test(path) && method === "POST") {
      const thread = data.threads.find(
        (item) => item.thread_id === path.split("/")[3],
      );
      if (!thread)
        return this.json(
          route,
          { error: { code: "not_found", message: "会话不存在" } },
          404,
        );
      const { request_id } = body as { request_id: string };
      if (request_id !== thread.active_request_id)
        return this.json(
          route,
          { error: { code: "request_conflict", message: "恢复标识不匹配" } },
          409,
        );
      thread.active_request_id = null;
      thread.pending = false;
      thread.can_resume = false;
      thread.status = "completed";
      thread.messages.push({ role: "assistant", content: ANSWER });
      return this.json(route, this.result(thread.thread_id, request_id));
    }
    if (/^\/api\/records\/(metric|diet|exercise)$/.test(path)) {
      const kind = path.split("/")[3];
      if (method === "GET")
        return this.json(
          route,
          this.success({ records: data.records[kind], truncated: false }),
        );
      if (method === "POST") {
        const payload = body as {
          record: Omit<HealthRecord, "id">;
          request_id: string;
        };
        const record = { ...payload.record, id: UUID(this.nextId++) };
        data.records[kind].unshift(record);
        return this.json(route, this.success(record));
      }
    }
    if (path === "/api/documents" && method === "GET")
      return this.json(route, { documents: data.documents });
    if (
      (path === "/api/documents/upload" || path === "/api/documents/text") &&
      method === "POST"
    ) {
      const filename = path.endsWith("/text")
        ? (body as { filename: string }).filename
        : (/filename="([^"]+)"/.exec(request.postData() ?? "")?.[1] ??
          "synthetic.md");
      const document: HealthDocument = {
        id: UUID(this.nextId++),
        filename,
        created_at: DATE,
        document_type: filename.endsWith(".pdf") ? "pdf" : "md",
        parse_status: this.ingestionStatus === "indexed" ? "parsed" : "failed",
        index_status: this.ingestionStatus,
        error_code: this.ingestionStatus === "failed" ? "document_empty" : null,
        visibility: "private",
      };
      data.documents.unshift(document);
      return this.json(route, document);
    }
    if (path === "/api/memory" && method === "GET")
      return this.json(route, data.memory);
    if (path.startsWith("/api/memory/") && ["PUT", "DELETE"].includes(method)) {
      const key = path.split("/")[3];
      const value =
        method === "DELETE" ? null : (body as { value: string }).value;
      data.memory.preferences = data.memory.preferences.filter(
        (item) => item.key !== key,
      );
      if (value !== null)
        data.memory.preferences.push({
          key,
          value,
          updated_at: DATE,
          source_request_id: UUID(this.nextId++),
          source_thread_id: null,
        });
      return this.json(route, { changes: [{ key, value }] });
    }
    this.unexpected.push(`${method} ${path}`);
    return this.json(
      route,
      {
        error: { code: "unexpected_test_request", message: "测试未声明此接口" },
      },
      501,
    );
  }

  private createThread(data: OwnerData): ThreadState {
    const thread: ThreadState = {
      thread_id: UUID(this.nextId++),
      title: "新对话",
      created_at: DATE,
      active_request_id: null,
      messages: [],
      pending: false,
      can_resume: false,
    };
    data.threads.unshift(thread);
    return thread;
  }

  private result(threadId: string, requestId: string): ChatResult {
    return {
      answer: ANSWER,
      thread_id: threadId,
      request_id: requestId,
      trace_id: TRACE,
      run_id: RUN,
      model_mode: "fake",
      termination_reason: "completed",
      memory_updates: [],
    };
  }

  private success<T>(data: T) {
    return {
      success: true,
      data,
      error_code: null,
      error_message: null,
      retryable: false,
    };
  }
}
