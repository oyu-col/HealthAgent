- 对应源码：`backend/app/agent/tool_middleware.py`
- 核对日期：2026-10-04
- 阅读源码：[tool_middleware.py](../../../../backend/app/agent/tool_middleware.py)
- 所属目录：[目录说明](README.md)

# 工具返回规范化与重复无进展保护

## 定位与设计目的

ToolBoundaryMiddleware 是图工具调用的最外层业务边界：把框架验证和下游异常转成统一 ToolResult，让模型能依据 error_code 修正策略；同时生成可见工具状态和无进展检测。

## 一次调用的真实过程

1. 记录起始时间，读取工具名和调用 ID，通过 get_stream_writer 发 tool.started，不包含参数。
2. await 内层 handler（可能包含框架重试、超时和工具限额）。
3. 如果框架返回 status=error 的 ToolMessage，规范为 validation_error；否则按 JSON 解析 ToolResult。
4. 分类捕获错误并构造结果，记录只含名称/成功/错误码/耗时的日志，发送 tool.finished。
5. 将工具名、原参数、完整规范化结果序列化并计算 SHA-256 指纹；同一上下文某指纹第三次出现，抛 no_progress/503。
6. 返回新 ToolMessage，保留调用 ID 和名称，status 与 result.success 一致。

## 重要异常分支

GraphBubbleUp 和 AgentError 原样抛出，保留框架控制流及预算中止语义。ValidationError 变成固定参数错误；RetryableToolResult 取其已经脱敏的业务结果。
写工具遇瞬态异常或 OperationalError，返回 write_outcome_unknown 且不可自动重试：超时并不能证明数据库没提交。其他 OperationalError 返回 storage_unavailable，retryable 取瞬态判断；其余瞬态异常返回 tool_timeout/retryable=true；未知错误返回固定 tool_error。
CancelledError 不属于被捕获的普通 Exception，会继续传播。因此取消或预算中止时不保证一定产生 tool.finished，不能用缺少 finished 推断工具从未开始。

## 状态、隐私与设计取舍

指纹在运行内存中使用参数和结果，但日志和 SSE 不输出它们，Trace 也不以这些原文持久化。无进展检测包含成功结果：重复三次相同读取也会被停止，不只检测失败。不同调用 ID 不参与指纹，因此换 ID 不能绕过循环检测。
子 Agent 使用独立 tool_observations，但预算仍共享。这里不是写入去重实现；持久幂等在业务 Service/Repository，不能用循环指纹代替事务回执。

## 验证与修改注意

健康工具测试覆盖真实写入和统一结果，可靠性测试覆盖重试/未知写结果，流式测试确认不泄露参数。改变规范化顺序需检查框架 ToolMessage 错误与本项目 JSON 错误的区别，避免把下游失败伪装成功。

## 相关源码说明

- [backend/app/agent/reliability.py](reliability.py.md)
- [backend/app/agent/context.py](context.py.md)
- [backend/app/domain/schemas.py](../domain/schemas.py.md)
- [backend/tests/integration/test_health_tools.py](../../tests/integration/test_health_tools.py.md)
- [backend/tests/integration/test_reliability.py](../../tests/integration/test_reliability.py.md)
- [backend/tests/integration/test_streaming.py](../../tests/integration/test_streaming.py.md)

