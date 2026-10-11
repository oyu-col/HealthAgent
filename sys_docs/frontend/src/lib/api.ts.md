# 同源 HTTP 客户端与严格 SSE 解码器

- 对应源码：`frontend/src/lib/api.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/lib/api.ts) · [本目录说明](README.md)

## 统一接口

文件导出 ApiError、requestJson<T> 和 streamChat。所有业务组件通过这里访问后端，不各自拼接外部服务 URL 或保存凭据。ApiError 除 Error.message 外携带 status、code、traceId、threadId、requestId，便于区分认证失败、网络中断与可定位的业务失败。

## 同源与凭据规则

localPath 以一个固定无效站点作 URL 解析基准，只允许以单斜杠开头的本站 /api、/api/... 或 /healthz。拒绝完整外站 URL、双斜杠、反斜杠、hash 和规范化后离开 API 路径的地址。它是客户端调用边界，不能替代后端鉴权。

fetchApi 先删除调用者 headers 中的 Authorization，再按当前 token.trim() 添加 Bearer，避免带入旧身份。默认 Accept 为 application/json；字符串 body 默认 Content-Type 为 application/json；FormData 一律移除 Content-Type，让浏览器补充 boundary。请求固定 credentials=same-origin、redirect=error、cache=no-store，避免跟随重定向携带凭据或缓存健康响应。

取消前先检查 signal。网络异常被转换为固定中文消息，不回显底层网络信息；AbortError 保持原语义。没有把 token 存入浏览器存储或日志的代码。

## JSON 响应与安全错误

requestJson 检查 HTTP 状态及 JSON Content-Type；204 返回 undefined。成功响应解析为 unknown 后转换为调用者指定 T：这是 TypeScript 类型断言，不是对所有业务 JSON 做运行时 schema 验证。

responseError 只尝试解析 JSON 错误体，按标准 error.code/message 和恢复标识构造 ApiError；消息最长 2000 字符。X-Trace-ID 可作为回退，标识需符合 1–128 个字母数字、下划线或连字符。代理 HTML 不会作为消息展示。非 JSON 成功响应、损坏 JSON 和 HTTP 失败都有明确错误码。

## SSE：从字节到帧

streamChat 发送 POST /api/chat/stream，并要求 text/event-stream 与可读 body。TextDecoder 使用 UTF-8 严格增量模式，确保跨网络 chunk 的中文多字节不乱码。EventDecoder 把网络字符拆成 SSE 行和帧：

- 支持 LF、CRLF；chunk 末尾单独的 CR 留到下一次判断。
- 注释行不作为事件；多条 data 行以换行拼接；多个完整帧可来自一个网络 chunk。
- 只有空行才结束一帧；EOF 不能替缺少的空行完成提交。
- 单帧累计字符不超过 1024×1024，包括未结束缓冲，防止无限积累。
- 只接受当前六种协议事件，不把未知事件静默当作成功。

## SSE：协议完整性

序号从 1 严格递增；version 必须为 1；trace/run/thread/request 身份需保持一致。run.started 前只允许 run.started 或准备阶段 run.failed；启动后每个事件必须有一致的非空运行、线程、请求标识。run.started 还验证 model_mode。工具事件必须有工具名和调用 ID；tool.finished 要求 success 布尔值。

run.completed 要求非空 answer、termination_reason=completed、与开始一致的 model_mode，以及合法的 memory_updates 数组。只有完整通过校验后才调用 UI 的 onEvent；完整成功帧才返回 ChatResult。run.failed 先传递事件，再抛出带恢复信息的 ApiError。

## 失败、取消与资源回收

无完成事件的 EOF 为 stream_incomplete；错误字节、畸形 JSON、超帧大小、身份串流或序号异常为 invalid_stream。它们均尽可能保留服务端 threadId 和原 requestId。signal abort 时取消 pending reader，使停止按钮不必等新字节；finally 移除监听、取消 reader 并 releaseLock。成功帧到达后也主动关闭传输，不等待远端永久连接结束。

相关说明：[Chat 恢复流程](../components/Chat.tsx.md)、[协议类型](types.ts.md)、[传输单元测试](../../tests/unit/api.test.ts.md)。

