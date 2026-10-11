# stream_client.py：最小 POST SSE 客户端

- 对应源码：`backend/scripts/stream_client.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[stream_client.py](../../../backend/scripts/stream_client.py)

## 参数和请求

--url 默认 http://127.0.0.1:8000；--message 必填；--thread-id 和 --request-id 可选。main 将 message/thread_id/request_id 组成 JSON，POST 到 /api/chat/stream。客户端 token 从独立 HEALTH_AGENT_CLIENT_TOKEN 环境变量读取，存在时才加 Authorization Bearer；这不是后端模型 key。

使用 httpx.stream，同步读取字节块，HTTP 超时参数为 310 秒；这是网络阶段/读操作的超时设置，不是整个流固定 310 秒的总 deadline。HTTP 非成功先 raise_for_status，再把每个 bytes chunk 交给正式 [SSEDecoder](../app/api/sse.py.md)，避免按网络 chunk 直接解析 JSON 或破坏 UTF-8 字符。

## 事件处理

message.delta 立即输出 text；run.started 将 thread/request 标识写 stderr，便于记录后续恢复身份；run.completed 输出完整权威答案并置 completed；run.failed 以错误码和固定消息退出。工具事件会被解码但这个精简终端客户端不负责渲染它们。

流结束时如果从未收到 completed，明确失败并提示沿 request_id 恢复，不能把 EOF 当成功。脚本不做 Last-Event-ID 事件重放、不自动重连，也不自动改变 request_id 重发写请求。它用来验证协议及手动调试，完整交互状态机在 [前端 api.ts](../../frontend/src/lib/api.ts.md)。

本脚本没有 --resume 专用命令。可以沿用原 --request-id、相同 --message 重发，由 ThreadService 恢复/回放；也可手工调用 /api/threads/{id}/resume。不传 --request-id 时由后端生成，若在 run.started 前断线，脚本未必取得该 ID，因此需要可恢复操作时宜在首次调用明确提供。

运行该脚本会实际创建/继续服务上的会话；URL 指向何处就使用哪里的服务、身份和数据，默认回环地址本身不产生隔离测试数据库。
