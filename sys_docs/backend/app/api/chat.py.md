- 对应源码：`backend/app/api/chat.py`
- 核对日期：2026-10-11
- 阅读源码：[chat.py](../../../../backend/app/api/chat.py)
- 所属目录：[目录说明](README.md)

# 普通对话入口与公共执行流程

## 定位与设计目的

提供 `GET /healthz`、`POST /api/chat`，并把会话准备、执行、回执完成封装为 `execute_chat`，供恢复接口复用。路由不自己实现 Agent 循环，也不直接写健康记录。

## 关键入口

- `healthz` 返回 Phase 12 和模型模式，只检查应用可用性，不探测收费 provider，也不自动运行Benchmark。
- `chat` 接收 ChatRequest，将 UUID 转成服务层使用的字符串，并传入由 UserDependency 验证的 user_id。
- `chat_response` 从 prepared.context 取执行标识和 memory_updates，构造统一成功响应。
- `execute_chat` 同时支持普通 message 和 `resume=True`。

## 实际执行顺序

1. 对 message 再做配置级长度检查，超长直接抛 invalid_request/422。
2. 进入 ThreadService.prepare 异步上下文，由服务负责归属、并发 admission、请求去重和恢复准备。
3. 将 thread_id/request_id 写入 request.state，使全局错误处理也能返回恢复信息。
4. 无缓存答案时调用 Runtime.ainvoke；存在缓存则调用 Runtime.record_cached，记录本次回放而不再调用模型。
5. ThreadService.complete 保存完成回执，然后返回 ChatResponse。
6. 任意 BaseException 都先以 asyncio.shield 调用 threads.fail，再原样抛出。

## 状态、错误和幂等边界

request_id 的去重策略在 ThreadService/Repository 内，路由只保持标识贯穿。用 BaseException 是为了包括任务取消；shield 避免故障状态更新被同一取消直接打断。失败不回滚已经完成的健康写入，恢复依赖 checkpoint 和工具幂等回执。
业务错误最终由 main.py 的异常处理转成 ErrorResponse；路由声明的响应码包括 401、404、409、422、500、502、503、504。缓存回放也可能因 Trace 持久化不可用而失败，不能理解为完全跳过后端执行管理。

## 验证与修改注意

API 测试覆盖健康探针、OpenAPI、请求隔离和脱敏错误；Thread 测试覆盖重启恢复及重复请求。调整执行顺序时尤其不能先返回成功再保存完成回执。

## 相关源码说明

- [backend/app/api/threads.py](threads.py.md)
- [backend/app/services/threads.py](../services/threads.py.md)
- [backend/app/agent/runtime.py](../agent/runtime.py.md)
- [backend/tests/integration/test_api.py](../../tests/integration/test_api.py.md)
- [backend/tests/integration/test_threads.py](../../tests/integration/test_threads.py.md)

