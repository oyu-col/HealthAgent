- 对应源码：`backend/app/api/stream.py`
- 核对日期：2026-10-04
- 阅读源码：[stream.py](../../../../backend/app/api/stream.py)
- 所属目录：[目录说明](README.md)

# 对话 SSE 流式传输入口

## 定位与设计目的

实现 `POST /api/chat/stream`，将 Runtime 的框架流转换成面向前端的六类 SSE 事件。它处理会话生命周期和终态承诺，SSE 字符编码交给 sse.py。

## 输入与返回

请求体与普通对话一致，身份由 UserDependency 注入。返回 StreamingResponse，content-type 为 text/event-stream，并设置 `X-Accel-Buffering: no` 与 `Cache-Control: no-store`。
所有事件带 version=1、seq、trace_id、run_id、thread_id；prepare 成功后还带 request_id。序号由内部 frame 函数逐帧递增。

## 真实执行流程

1. 在开始流之前检查输入配置长度，并对已传入 thread_id 检查归属。
2. events 生成器进入 threads.prepare，建立本次执行标识；先发 run.started。
3. 无缓存时遍历 Runtime.astream；message.delta、tool.started、tool.finished 直接包装转发，内部 answer 事件只保存最终答案而不原样发给客户端。
4. 有缓存时记录 cached Trace；两种路径都必须等待 threads.complete 完成。
5. 设置 completed 标志，再发 run.completed；其 answer 是权威终值，不能由客户端简单拼接所有中间文字代替。
6. 未完成时发生 BaseException，先 shield 保存失败状态，再向外传播；AgentError 和普通 Exception 被转换为 run.failed。

## 错误与取消边界

建立流后，即使 HTTP 是 200，业务仍可能以 run.failed 结束。prepare 阶段失败可能尚无 run_id，因此这些标识允许空值。只有路由前置校验失败可通过普通 HTTP 错误直接返回。
任务取消不会被普通 Exception 分支吞掉；aclosing 会关闭框架异步流。run.completed 发送前已完成会话回执，因此客户端即使未收到最后一帧，也应沿原 request_id 查询/恢复，不能生成新 ID 重做业务。
当前不实现心跳、Last-Event-ID 历史重放或服务器事件队列。seq 用于本次连接顺序校验，不是跨连接恢复游标。

## 验证与修改注意

流式测试覆盖中文逐字节解码、事件顺序、权威终值、工具参数不泄露、失败无 completed，以及取消关闭模型并释放会话。修改事件字段时同步 Python 客户端与前端解析器。

## 相关源码说明

- [backend/app/api/sse.py](sse.py.md)
- [backend/app/agent/runtime.py](../agent/runtime.py.md)
- [backend/app/services/threads.py](../services/threads.py.md)
- [backend/tests/integration/test_streaming.py](../../tests/integration/test_streaming.py.md)
- [frontend/src/lib/api.ts](../../../frontend/src/lib/api.ts.md)

