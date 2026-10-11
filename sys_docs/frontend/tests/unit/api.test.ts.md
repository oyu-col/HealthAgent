# HTTP 与 SSE 传输契约的单元测试

- 对应源码：`frontend/tests/unit/api.test.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/tests/unit/api.test.ts) · [本目录说明](README.md)

## 测试对象和隔离方式

Vitest 在 Node 环境中直接导入 ApiError、requestJson、streamChat，使用 vi.stubGlobal 替换 fetch。mockJson 构造 Response，mockStream 构造 ReadableStream 并记录 cancel；afterEach 恢复所有全局替身，避免不同用例污染。输入问题、token、线程及 Trace 标识全部为合成值。

当前文件按 it.each 展开后设计为 33 个用例。本页是源码解释，不表示本次文档任务重新执行并得到该通过数。

## JSON 请求组验证什么

| 场景 | 断言的实际行为 |
|---|---|
| 同源 JSON + bearer | URL、JSON Content-Type、去空白后的 Bearer、禁止重定向和 no-store |
| 空 token | 删除调用者残留 Authorization，防止身份串用 |
| FormData | body 保持原对象，移除错误 Content-Type，让 fetch 生成 boundary |
| 6 个非法路径 | 外站 URL、双斜杠、路径跳出、反斜杠、非 API、相对路径在 fetch 前被拒绝 |
| 标准业务错误 | 保留 HTTP 409、业务码、安全消息及 trace/thread/request 标识 |
| HTML 代理错误 | HTTP 502 使用安全错误，不展示代理原文；200 HTML 判 invalid_response |
| 损坏 JSON / 网络异常 | 输出固定类别与安全消息，不泄露底层异常 |
| 204 删除 | 返回 undefined，不强行解析空 body |

组内示例 /api/health/metrics 等只是用于验证传输约束的合法本站路径，不声明当前后端一定存在同名路由。

## SSE 组验证什么

1. 将包含中文、CRLF、注释、多行 data 的事件逐字节切分；最终答案与临时片段不同，证明采用 completed.answer。
2. 一个 chunk 放入多个工具事件，完成后连接仍未关闭；客户端必须主动 cancel 且解锁 reader。
3. 干净 EOF 没有完成事件时拒绝成功，并保留恢复标识；缺最终空行的 completed 也不能提交。
4. run.failed 显示标准错误；准备阶段还没有 run.started、run/thread 为 null 时允许失败。
5. 8 个污染事件分别改重复/跳跃 seq、version、trace/thread/request/run 身份或 text 类型；在回调前拒绝，旧状态不应被污染。
6. 非法 JSON 与超过 1 MiB 字符预算的帧被拒绝，超限时关闭连接。
7. 401 在开流前正确转换；AbortSignal 取消等待 reader 并释放锁；已经取消时完全不 fetch。
8. 网络在响应前失败时保留调用者原 thread/request 身份；ApiError 仍然是普通 Error 的子类。

## 能力边界

该文件不挂载 React，不测试按钮可访问性、导航、数据库幂等或真实网络代理。取消测试证明客户端释放流，不能证明服务端业务自动回滚。工具调用成功字段的合成帧也不等于真实工具执行。跨组件验证与真实后端 smoke 需看另外两条路径。

相关说明：[被测 API](../../src/lib/api.ts.md)、[浏览器测试](../e2e/workspace.spec.ts.md)、[真实 smoke](../../scripts/smoke.mjs.md)。

