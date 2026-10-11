- 对应源码：`backend/tests/integration/test_streaming.py`
- 核对日期：2026-10-04
- 阅读源码：[test_streaming.py](../../../../backend/tests/integration/test_streaming.py)
- 所属目录：[目录说明](README.md)

# SSE 增量事件、脱敏与取消清理测试

## 测试结构

StreamingModel 继承 SpyChatModel，真正实现异步 _astream，按“合成/中文/回答”产生 AIMessageChunk，并用 _started 事件标记已进入模型。parse_events 把 HTTP 内容逐字节喂给 SSEDecoder，刻意覆盖中文 UTF-8 跨块边界。

## 四项主要验证

| 测试 | 关键断言 |
| --- | --- |
| test_native_stream_to_sse_and_incremental_utf8_client | 响应为 text/event-stream，首 started、尾 completed；所有 delta 拼出预期中文，seq 从 1 连续增加；completed.answer 与之后查询到的 checkpoint 助手消息一致。 |
| test_stream_tool_events_do_not_expose_arguments | 确定性查询工具产生 tool.started/tool.finished；最终工具观测成功；事件 data 不暴露 arguments。 |
| test_stream_errors_are_terminal_and_safe | 注入带 SECRET 的模型异常，尾事件为 run.failed，全文不包含 SECRET，且没有 run.completed。 |
| test_stream_cancellation_closes_model_and_releases_thread | 在 threads.prepare 内直接迭代 Runtime.astream，等模型 _started 后取消 anext 任务并关闭流；断言模型已取消、线程活跃集合为空。 |

## 覆盖边界

ASGITransport 在本测试里收集响应后解析，能验证事件内容和编码但不精确测量浏览器逐 token 到达时延。取消用例直接测试 Runtime/Thread 的清理路径，不是通过真实 TCP 断连触发。
注入的 StreamingModel 是测试专用，不能据此把 DemoChatModel 描述成真实流式生成模型。工具参数不在事件里，也不等于最终模型回答必然不引用用户提供的事实；两个边界应分开理解。

## 修改注意

修改 event 名、version/seq、最终答案、异常包装或 aclosing 时同步更新本文件以及前端 API 单元测试。不要以等待固定 SQLite 时长代替 _started 同步，避免慢机器下偶发取消时机错误。

## 相关源码说明

- [backend/app/api/stream.py](../../app/api/stream.py.md)
- [backend/app/api/sse.py](../../app/api/sse.py.md)
- [backend/app/agent/runtime.py](../../app/agent/runtime.py.md)
- [backend/app/services/threads.py](../../app/services/threads.py.md)
- [frontend/src/lib/api.ts](../../../frontend/src/lib/api.ts.md)

