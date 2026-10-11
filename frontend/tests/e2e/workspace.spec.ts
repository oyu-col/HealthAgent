import { expect, test as base } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { ALICE_TOKEN, ANSWER, BOB_TOKEN, MockApi, TRACE } from "./mock-api";

const test = base.extend<{ api: MockApi }>({
  api: async ({ page }, runFixture) => {
    const api = new MockApi();
    await api.install(page);
    await runFixture(api);
    expect(
      api.unexpected,
      "Every API call must use the declared offline contract",
    ).toEqual([]);
  },
});

test("Chinese SSE commits only the final answer and persisted threads can be reopened", async ({
  page,
  api,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /^新对话/ }).click();
  const composer = page.getByPlaceholder(/记录今天的状态/);
  await composer.fill("今天想整理睡眠观察");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByText(ANSWER, { exact: true })).toBeVisible();
  expect(
    api.requests.filter((request) => request.path === "/api/chat/stream"),
  ).toHaveLength(1);
  const input = api.requests.find(
    (request) => request.path === "/api/chat/stream",
  )?.body;
  expect(input).toMatchObject({
    message: "今天想整理睡眠观察",
    request_id: expect.stringMatching(/^[\da-f-]{36}$/),
  });
  await page.reload();
  await page.getByRole("button", { name: /今天想整理睡眠观察/ }).click();
  await expect(page.getByText(ANSWER, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /合成用户 Alice 的健康观察/ }).click();
  await expect(
    page.getByText("这是 Alice 的历史问题", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("这是 Alice 的历史回答", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(ANSWER, { exact: true })).toHaveCount(0);
});

test("EOF without completion keeps the same request identity for explicit checkpoint recovery", async ({
  page,
  api,
}) => {
  api.streamMode = "incomplete";
  await page.goto("/");
  await page.getByRole("button", { name: /^新对话/ }).click();
  await page
    .getByPlaceholder(/记录今天的状态/)
    .fill("请整理这一轮的合成健康记录");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(/中断|完整回答/);
  await expect(page.getByText(ANSWER, { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: /恢复/ }).click();
  await expect(page.getByText(ANSWER, { exact: true })).toBeVisible();
  const submissions = api.requests.filter(
    (request) => request.path === "/api/chat/stream",
  );
  expect(submissions).toHaveLength(1);
  const input = submissions[0].body as { request_id: string };
  const resumes = api.requests.filter((request) =>
    request.path.endsWith("/resume"),
  );
  expect(resumes).toHaveLength(1);
  expect(resumes[0].body).toEqual({ request_id: input.request_id });
});

test("record form validates input then writes an idempotent record and refreshes the list", async ({
  page,
  api,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "健康记录", exact: true }).click();
  await page.getByRole("button", { name: "添加记录", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "添加身体指标" });
  await dialog.getByRole("button", { name: "保存记录" }).click();
  expect(
    api.requests.filter(
      (request) =>
        request.path === "/api/records/metric" && request.method === "POST",
    ),
  ).toHaveLength(0);
  await dialog.getByLabel("数值（kg）", { exact: true }).fill("67.3");
  await dialog.getByRole("button", { name: "保存记录" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(
    page.locator(".record-row").filter({ hasText: "67.3" }),
  ).toContainText("体重");
  const writes = api.requests.filter(
    (request) =>
      request.path === "/api/records/metric" && request.method === "POST",
  );
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toEqual({
    record: {
      metric_type: "weight",
      value: 67.3,
      unit: "kg",
      measured_at: expect.stringMatching(/Z$/),
    },
    request_id: expect.stringMatching(/^[\da-f-]{36}$/),
  });
  expect(
    api.requests.filter(
      (request) =>
        request.path === "/api/records/metric" && request.method === "GET",
    ).length,
  ).toBeGreaterThanOrEqual(2);
});

test("failed document indexing is actionable and successful upload enables a draft question", async ({
  page,
  api,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "我的文档", exact: true }).click();
  api.ingestionStatus = "failed";
  await page.getByLabel("选择健康文档").setInputFiles({
    name: "failed.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("synthetic unreadable PDF"),
  });
  await expect(page.getByRole("alert")).toContainText("未能建立索引");
  await expect(
    page.getByRole("button", { name: "询问文档 failed.pdf" }),
  ).toBeDisabled();
  await expect(page.locator(".success-notice")).toHaveCount(0);
  api.ingestionStatus = "indexed";
  await page.getByLabel("选择健康文档").setInputFiles({
    name: "observations.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# 合成健康笔记\n这是浏览器契约测试中的合成资料。"),
  });
  await expect(
    page.getByRole("status").filter({ hasText: "已就绪" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "询问文档 observations.md" }).click();
  await expect(page.getByPlaceholder(/记录今天的状态/)).toHaveValue(
    /observations\.md/,
  );
  expect(
    api.requests.filter((request) => request.path === "/api/chat/stream"),
  ).toHaveLength(0);
});

test("a note with no index cannot claim successful indexing", async ({
  page,
  api,
}) => {
  api.ingestionStatus = "failed";
  await page.goto("/");
  await page.getByRole("button", { name: "我的文档", exact: true }).click();
  await page.getByRole("button", { name: "新建笔记", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "新建健康笔记" });
  await dialog.getByLabel("笔记名称").fill("failed-note");
  await dialog
    .getByLabel("内容", { exact: true })
    .fill("这是用于验证索引失败的合成笔记。");
  await dialog.getByRole("button", { name: "保存笔记" }).click();
  await expect(
    page.getByRole("button", { name: "询问文档 failed-note.md" }),
  ).toBeDisabled();
  await expect(page.locator(".success-notice")).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText(/索引|未就绪/);
});

test("memory is saved through PUT and deletion waits for confirmation", async ({
  page,
  api,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "长期偏好", exact: true }).click();
  await page.getByRole("button", { name: /回答风格.*阅读习惯/ }).click();
  await page
    .getByRole("dialog", { name: "设置回答风格" })
    .getByLabel("选择偏好")
    .selectOption("detailed");
  await page.getByRole("button", { name: "保存偏好", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /回答风格.*详细解释/ }),
  ).toBeVisible();
  expect(
    api.requests.find((request) => request.method === "PUT")?.body,
  ).toEqual({ value: "detailed" });
  await page.getByRole("button", { name: /回答风格.*详细解释/ }).click();
  await page.getByRole("button", { name: "忘记", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "忘记回答风格" }),
  ).toBeVisible();
  expect(
    api.requests.filter((request) => request.method === "DELETE"),
  ).toHaveLength(0);
  await page.getByRole("button", { name: "确认忘记", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /回答风格.*尚未设置/ }),
  ).toBeVisible();
  expect(
    api.requests
      .filter((request) => request.method === "DELETE")
      .map((request) => request.path),
  ).toEqual(["/api/memory/response_style"]);
});

test("changing credentials removes the previous user's workspace and never persists tokens", async ({
  page,
  api,
}) => {
  api.requireAuth = true;
  await page.goto("/");
  await page.getByLabel("访问凭据", { exact: true }).fill(ALICE_TOKEN);
  await page.getByRole("button", { name: "连接工作空间", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /合成用户 Alice 的健康观察/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /合成用户 Alice 的健康观察/ }).click();
  await expect(
    page.getByText("这是 Alice 的历史回答", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "更换访问凭据", exact: true }).click();
  await expect(
    page.getByText("这是 Alice 的历史回答", { exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("访问凭据", { exact: true }).fill(BOB_TOKEN);
  await page.getByRole("button", { name: "连接工作空间", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /合成用户 Bob 的独立会话/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /合成用户 Alice 的健康观察/ }),
  ).toHaveCount(0);
  await expect(
    page.getByText("这是 Alice 的历史回答", { exact: true }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage },
    })),
  ).toEqual({ local: {}, session: {} });
});

test("narrow screens expose navigation and fit records without horizontal overflow", async ({
  page,
  api,
}) => {
  void api;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await page.getByRole("button", { name: "健康记录", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "每一天，都有迹可循" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "添加记录", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "添加身体指标" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("trace details retain unknown measurements and explicitly label failed events", async ({
  page,
  api,
}) => {
  await page.goto("/");
  await page.getByPlaceholder(/记录今天的状态/).fill("查看合成执行记录");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByText(ANSWER, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /查看执行记录/ }).click();
  const dialog = page.getByRole("dialog", { name: "执行记录", exact: true });
  await expect(dialog.getByText(TRACE, { exact: true })).toBeVisible();
  await expect(dialog.getByText("已中断", { exact: true })).toBeVisible();
  await expect(
    dialog
      .locator(".trace-metrics > div")
      .filter({ hasText: "模型 / 工具" })
      .locator("strong"),
  ).toHaveText("— / —");
  for (const label of ["总耗时", "专业委派", "可观测重试"])
    await expect(
      dialog
        .locator(".trace-metrics > div")
        .filter({ hasText: label })
        .locator("strong"),
    ).toHaveText("—");
  await expect(dialog.getByText("不可完整观测", { exact: true })).toBeVisible();
  await expect(dialog.getByText("尚未结束", { exact: true })).toBeVisible();
  await expect(dialog.getByText(/缺失部分不能视为未发生/)).toBeVisible();
  const failed = dialog
    .locator(".trace-timeline li")
    .filter({ hasText: "query_health_metrics" });
  await expect(failed).toContainText("失败");
  await expect(failed.locator(".event-dot")).toHaveClass(/failed/);
  await expect(
    dialog.locator(".trace-timeline li").filter({ hasText: "模型调用结束" }),
  ).toContainText("成功");
  await expect(
    dialog.locator(".trace-timeline li").filter({ hasText: "开始执行" }),
  ).not.toContainText(/成功|失败/);
  // React StrictMode may mount the read effect twice in the development build.
  const traceReads = api.requests.filter(
    (request) => request.path === `/api/traces/${TRACE}`,
  );
  expect(traceReads.length).toBeGreaterThanOrEqual(1);
  expect(traceReads.length).toBeLessThanOrEqual(2);
  expect(traceReads.every((request) => request.method === "GET")).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("desktop and mobile workspace screenshots expose usable layouts", async ({
  page,
  api,
}) => {
  void api;
  const directory = "test-results/ui-review";
  await mkdir(directory, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /从今天开始/ })).toBeVisible();
  await page.screenshot({
    path: `${directory}/desktop-welcome.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.getByPlaceholder(/记录今天的状态/).fill("整理今天的合成观察");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByText(ANSWER, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /查看执行记录/ }).click();
  await expect(
    page
      .getByRole("dialog", { name: "执行记录", exact: true })
      .getByText("不可完整观测", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `${directory}/desktop-trace.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "打开导航", exact: true }),
  ).toHaveAttribute("aria-expanded", "true");
  await page.getByRole("button", { name: /^新对话/ }).click();
  await expect(page.getByRole("heading", { name: /从今天开始/ })).toBeVisible();
  await page.screenshot({
    path: `${directory}/mobile-welcome.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await page.getByRole("button", { name: "健康记录", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "每一天，都有迹可循" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开导航", exact: true }),
  ).toHaveAttribute("aria-expanded", "false");
  await page.screenshot({
    path: `${directory}/mobile-records.png`,
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
