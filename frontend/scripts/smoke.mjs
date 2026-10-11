import { chromium, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const base = new URL(process.argv[2] ?? "");
if (base.protocol !== "http:" || base.hostname !== "127.0.0.1")
  throw new Error("Smoke requires an isolated loopback server");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const failures = [];
page.on("pageerror", (error) => failures.push(error.message));
const checks = [];
try {
  await page.goto(base.href);
  await expect(page.getByRole("heading", { name: /从今天开始/ })).toBeVisible();
  await expect(page.getByText("演示模式", { exact: true })).toBeVisible();
  await mkdir("test-results/real-ui", { recursive: true });
  await page.screenshot({
    path: "test-results/real-ui/welcome.png",
    fullPage: true,
  });
  checks.push("built_static_ui");

  await page.getByRole("button", { name: "健康记录", exact: true }).click();
  await page.getByRole("button", { name: "添加记录", exact: true }).click();
  await page.getByLabel("数值（kg）", { exact: true }).fill("67.3");
  await page.getByRole("button", { name: "保存记录", exact: true }).click();
  await expect(page.locator(".record-row")).toContainText("67.3");
  const saved = await page.request.get(
    new URL("/api/records/metric", base).href,
  );
  expect(
    (await saved.json()).data.records.some((record) => record.value === 67.3),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/real-ui/records.png",
    fullPage: true,
  });
  checks.push("form_to_real_database");

  await page.getByRole("button", { name: "我的文档", exact: true }).click();
  await page.getByRole("button", { name: "新建笔记", exact: true }).click();
  await page.getByLabel("笔记名称", { exact: true }).fill("浏览器合成笔记");
  await page
    .getByLabel("内容", { exact: true })
    .fill("这是软件验证使用的合成健康笔记，不含真实健康资料。");
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect(
    page.locator(".document-row").filter({ hasText: "浏览器合成笔记" }),
  ).toContainText("可检索");
  checks.push("document_ingestion_index");

  await page.getByRole("button", { name: "长期偏好", exact: true }).click();
  await page.getByRole("button", { name: /回答风格/ }).click();
  await page.getByLabel("选择偏好", { exact: true }).selectOption("concise");
  await page.getByRole("button", { name: "保存偏好", exact: true }).click();
  await expect(
    page.locator(".preference-card").filter({ hasText: "回答风格" }),
  ).toContainText("简洁明了");
  checks.push("memory_preference_write");

  await page.getByRole("button", { name: /^新对话/ }).click();
  await page.getByPlaceholder(/记录今天的状态/).fill("浏览器流式合成测试");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message.assistant")).toContainText(
    "[FAKE 演示模式]",
    { timeout: 20000 },
  );
  await expect(
    page.getByRole("button", { name: /查看执行记录/ }),
  ).toBeVisible();
  const threadUrl = page.url();
  await page.getByRole("button", { name: /查看执行记录/ }).click();
  await expect(page.getByRole("dialog", { name: "执行记录" })).toContainText(
    "已完成",
  );
  await expect(page.locator(".trace-timeline")).toContainText("模型调用");
  await page.screenshot({
    path: "test-results/real-ui/trace.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "关闭弹窗", exact: true }).click();
  await page.reload();
  await expect(page.locator(".message.assistant")).toContainText(
    "[FAKE 演示模式]",
  );
  expect(page.url()).toBe(threadUrl);
  checks.push("real_sse", "persisted_thread_reload", "trace_timeline");
  await page.screenshot({
    path: "test-results/real-ui/chat.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await page.getByRole("button", { name: /^新对话/ }).click();
  await expect(page.getByRole("heading", { name: /从今天开始/ })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/real-ui/mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  checks.push("mobile_navigation_no_overflow");
  expect(failures).toEqual([]);
  console.log(
    JSON.stringify({
      status: "passed",
      checks,
      model_mode: "fake",
      mocked_api: false,
    }),
  );
} finally {
  await browser.close();
}
