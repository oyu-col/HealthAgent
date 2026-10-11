# 真实 FastAPI 与生产静态 UI 的浏览器联调脚本

- 对应源码：`frontend/scripts/smoke.mjs`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../frontend/scripts/smoke.mjs) · [本目录说明](README.md)

## 与普通 E2E 的区别

本脚本直接用 Playwright chromium.launch 启动浏览器，访问命令行传入 URL，没有安装 MockApi 路由。参数必须是 http 且 hostname=127.0.0.1，否则立即报错“Smoke requires an isolated loopback server”。它要求外部验收流程已启动独立测试后端、构建好前端并使用 fake 模式，本身不创建后端或临时数据库。

它会真实写入合成数据，因此不要指向自己日常使用的数据实例。回环地址校验只限制主机，并不验证数据库确实隔离；上层启动脚本仍需提供隔离数据目录。

## 验证过程

1. 访问生产入口，看到欢迎标题与“演示模式”，截图 welcome，记录 built_static_ui。
2. 通过 UI 写入 67.3 kg；再用 page.request 直接 GET /api/records/metric 核对列表含该值，记录 form_to_real_database。
3. 创建“浏览器合成笔记”，正文明确不是实际健康资料；文档行必须可检索，记录 document_ingestion_index。
4. 将回答风格设为 concise，页面呈现简洁明了，记录 memory_preference_write。
5. 发送合成消息，等待真实 SSE 显示 [FAKE 演示模式]；打开 Trace，确认已完成且时间线包含模型调用。
6. 保存线程 URL 并刷新，仍能读到 fake 助手历史且 URL 不变，记录 real_sse、persisted_thread_reload、trace_timeline。
7. 改到 390×844，抽屉新建对话、确认欢迎和无横向溢出，记录 mobile_navigation_no_overflow。

脚本监听 pageerror，末尾必须没有未捕获页面错误。finally 总会 browser.close。验证通过才输出 status=passed、checks、model_mode=fake、mocked_api=false 的 JSON。失败由断言/异常中止，不伪造通过状态。

## 输出和边界

截图写入 test-results/real-ui，包括 welcome、records、trace、chat、mobile。这里验证真实 HTTP、静态构建、表单入库、笔记索引、偏好写入、SSE、线程持久读取及 Trace；fake 模型不选择真实健康工具或专业委派，所以不能据此证明模型规划、医疗回答质量或 RAG 召回效果。

该脚本位于 scripts，为 .mjs，不属于 tsconfig 的类型检查范围或 pnpm lint 的 src/tests 路径。本次文档任务未执行它。

相关说明：[mock 浏览器测试](../tests/e2e/workspace.spec.ts.md)、[构建命令](../package.json.md)、[Chat](../src/components/Chat.tsx.md)。

