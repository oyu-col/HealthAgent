# Phase 9 — Frontend

交付日期：2026-10-03。范围依据 `HEALTH_AGENT_SPEC.md` 第 28 节 Phase 9 与用户将任务推进至 Phase 10 的最新要求。本阶段提供独立 HealthAgent 工作台，运行不依赖 DeerFlow。

## Completed

- 实现 Chat、Thread、Streaming、Documents、Health Records，并增加长期偏好管理和执行记录入口。
- 对话支持历史会话、中文增量消息、工具状态、停止、明确的未完成提示和原请求 checkpoint 恢复。以 `run.completed.answer` 提交最终回答，EOF 不视为成功。
- 健康记录页面直接读取 / 添加身体指标、饮食、运动；表单携带请求 UUID，提交成功后刷新真实列表。
- 文档支持 TXT / MD / PDF 上传与新建文本笔记。解析或索引失败保留失败状态，未就绪文档不能发起检索提问。
- 偏好支持查看、保存和确认后忘记；访问凭据切换会卸载旧工作空间。健康内容和凭据不写浏览器持久存储。
- 提供浅色 / 深色、移动导航、空白 / 加载 / 失败状态、输入法保护、可访问按钮和对话框。窄屏收起导航后使用 inert / aria-hidden，菜单反映展开状态并支持 Escape。
- 构建产物由 FastAPI 同源托管；开发服务器将 `/api` 代理到本地后端。Trace 弹窗显示真实服务端摘要 / 时间线，未知统计保留未知，失败事件有文本标识。

## Files Changed

- `frontend/package.json`、`pnpm-lock.yaml`、`tsconfig.json`、`vite.config.ts`、`eslint.config.js`、`index.html`、`AGENTS.md`：独立 React / TypeScript / Vite 工程与开发约定。
- `frontend/src/App.tsx`、`main.tsx`、`styles.css`、`components/Chat.tsx`、`Records.tsx`、`Documents.tsx`、`Memory.tsx`、`TraceDialog.tsx`、`ui.tsx`：工作台、业务页面和样式。
- `frontend/src/lib/api.ts`、`hooks.ts`、`types.ts`：同源请求、SSE 协议解析、请求取消和接口类型。
- `frontend/tests/unit/api.test.ts`：HTTP / SSE 传输边界验证。
- `frontend/playwright.config.ts`、`frontend/tests/e2e/global-setup.ts`、`mock-api.ts`、`workspace.spec.ts`：真实 Chromium 浏览器中的合成 API 契约测试与布局截图。
- `frontend/scripts/smoke.mjs`、`backend/scripts/smoke.py`：构建后页面连接真实临时本地服务的 smoke 流程。
- `backend/app/api/session.py`、`records.py`、`threads.py`、`schemas.py`、`backend/app/services/threads.py`、`backend/app/main.py`：可信身份、记录接口、可读会话状态与静态资源服务。
- `backend/tests/integration/test_ui_api.py`、`README.md`、[UI 参考记录](ui-deerflow-reference.md)：后端接口验证、启动说明和参考依据。

## Design

采用 React / TypeScript / Vite 与同源 FastAPI 的简单部署方式。左栏管理导航和会话，中间保留限宽阅读区，资料 / 偏好作为辅助面板；移动端按内容宽度折叠。只实现已有后端契约支持的入口，不引入另一套账号、模型配置或沙箱系统。

请求身份在发送前生成并保留；恢复沿用原 request_id，避免重放可能已经提交的健康记录。流中的临时文字与最终回答分别处理，工具事件仅展示允许的执行状态。页面内容始终来自 API，演示模式有明确标识。

凭据只在页面内存中保存，更换凭据中止请求并移除旧会话。Markdown 跳过原始 HTML，不自动加载模型生成的远程图片。失败读取不会被渲染为空记录；写入以服务端成功响应为准。

浏览器契约测试拦截所有 `/api` 请求，只使用合成用户与资料，未声明的接口会令测试失败。测试中的 Vite 使用 `createServer` 在 Playwright setup 进程中启动并在 teardown 中关闭，避免 Windows shell 子进程清理挂起；端口占用时明确失败，不关闭或复用未知服务器。

## DeerFlow Reference

详细源码路径、阅读位置及设计对应关系见 [DeerFlow UI 参考记录](ui-deerflow-reference.md)。主要借鉴：

| DeerFlow 模块 | 学习内容 | HealthAgent 调整 |
| --- | --- | --- |
| `workspace-sidebar.tsx`、`recent-chat-list.tsx` | 品牌 / 导航 / 最近会话 / 连接状态分区 | 独立轻量侧栏，使用后端可读标题与可信身份 |
| `welcome.tsx`、`chat-box.tsx`、`message-list.tsx` | 居中欢迎、限宽消息、移动面板 | 暖白与健康绿色，聊天居中，手机收起导航 |
| `input-box.tsx` | 圆角 composer、运行状态、停止、IME | 原生 textarea 与 HealthAgent SSE 恢复协议 |
| `core/threads/hooks.ts` | 完成 / 失败后的权威状态同步 | 单独 API / SSE 模块、AbortController、服务器 checkpoint |
| `artifact-viewer.tsx`、`memory-settings-page.tsx` | 资料状态、加载 / 错误分支、偏好管理 | 文档索引状态与枚举偏好表单 |

没有复制 DeerFlow 主体、修改参考仓库或将其包 / 服务接入运行。参考记录已说明任务从 Phase 1–6 UI 补充扩展至 Phase 10 的范围变化；最终交付范围以本文件及 Phase 7–10 记录为准。

## Tests

实际执行并通过（2026-10-03）：

- `pnpm test:e2e`：**10 passed (5.4s)，进程 exit=0**。覆盖中文 SSE 最终态与历史、EOF 原请求恢复、记录校验 / 单次 POST / 刷新、文档上传和笔记索引失败、偏好 PUT / 确认 DELETE、凭据切换隔离 / 无持久凭据、移动导航 / 无横向溢出、Trace 未知统计 / 显式失败、桌面与手机布局截图。
- 新增浏览器测试后再次执行 `pnpm lint`、`pnpm typecheck`：均 exit=0。
- 本轮主流程已执行 `pnpm test`：33 个传输单元测试通过；最终 `pnpm build`、`pnpm lint`、格式检查均通过。全量后端结果统一记录在 [Phase 7–10 验收记录](phase-7-10-validation.json)。
- 主代理实际执行最终 `python scripts/smoke.py --ui`：**12 项 API 检查 / 8 项浏览器检查通过，进程 exit=0**。使用构建后页面、真实 Uvicorn 与临时 SQLite；端口 49530，关联 trace `8d80692f-398b-4f22-927e-6abc4c201f9b`。服务器正常退出，临时数据已清理。此联调与上面的合成 API 浏览器测试分开记录，仍使用 fake 模型，不代表真实 provider 质量。
- 已生成 1440 × 1000 桌面和 390 × 844 手机截图：`frontend/test-results/ui-review/desktop-welcome.png`、`desktop-trace.png`、`mobile-welcome.png`、`mobile-records.png`。截图使用真实 Chromium、合成 API，关闭动画避免截到移动导航过渡帧；不将它们视为真实模型或医学质量评测。
- 主代理已目视检查上述 4 张截图及真实服务的桌面 / 对话 / Trace / 手机截图：布局正常，无横向溢出；Trace 失败有文字，未知统计未写为零。

初次 8 项用例通过后出现 Windows webServer 清理挂起；定位并停止该轮自身服务器后 runner 正常退出。直接 node 启动仍有清理问题，已改为上述进程内 Vite 生命周期，最终 10 项全量运行自行完成。Trace 初次测试因 React StrictMode 双次只读请求而失败，现按开发模式允许 1–2 次 GET，并保留各写操作严格单次断言。

## Known Issues

- fake 模型只用于流程回显，不执行真实自然语言健康分析；真实 provider 的医学回答、规划、检索质量尚未评测。
- 当前浏览器验收使用 Chromium；尚未做 Firefox / WebKit、屏幕阅读器或真实手机设备验收。
- 文档列表有状态及提问入口，尚无后端支持的原文引用详情查看器；未制造来源卡片。Trace 展示当前运行入口，完整跨会话 trace 浏览页尚未提供。
- 凭据仅保留内存，刷新后 token 模式需要重新连接。这是当前明确的会话策略。
- API 服务仍按单 worker 运行；页面不会扩大后端现有的并发与恢复承诺。

## Next Phase

Phase 10 的持久 Trace、工具 / 重试 / 耗时 / 终止原因实现与验证见 [Phase 10 交付记录](phase-10-delivery.md)。本轮按用户要求止于 Phase 10；下一阶段是 Phase 11 Domain Benchmark，需独立建立 20–30 个领域案例并按真实数据状态和证据评价。
