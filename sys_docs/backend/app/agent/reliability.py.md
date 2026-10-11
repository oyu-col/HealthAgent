- 对应源码：`backend/app/agent/reliability.py`
- 核对日期：2026-10-04
- 阅读源码：[reliability.py](../../../../backend/app/agent/reliability.py)
- 所属目录：[目录说明](README.md)

# 有界读取重试、共享模型预算与紧急规则

## 定位与设计目的

围绕框架原生 ToolRetryMiddleware 增加项目的重试分类、物理尝试预算和超时，避免自己重写退避循环。同时提供跨图模型调用预算与保守的紧急自述规则。

## 常量与失败分类

READ_TOOLS 含六类查询/检索/趋势工具；WRITE_TOOLS 含三类新增健康记录工具。TRANSIENT_CODES 只允许 storage_unavailable、retrieval_unavailable、tool_timeout。
transient_failure 接受超时、连接失败、httpx 网络错误、RetryableToolResult；HTTP/SDK 的 429 和 5xx 视为瞬态。SQLite OperationalError 仅锁定/忙等特定错误可重试，其他数据库错误不一概当瞬态。普通参数错误和鉴权拒绝不是重试对象。

## BoundedReadRetryMiddleware

构造时把可自动重试的工具限制为 READ_TOOLS，次数来自 tool_max_retries，采用框架指数退避（factor=2、max_delay=2）和 jitter；重试耗尽重新抛给外层边界。
每次 handler 实际尝试之前先 consume_tool。第二次及以后增加 budget.retries 并发出 tool.retry 元数据。单次尝试受 tool_timeout_seconds 限制；delegate_health_task 使用 subagent_timeout_seconds+0.1，再与请求总超时取较小值。
若只读工具正常返回 ToolMessage，但其中 ToolResult 标记 success=false、retryable=true 且错误码位于白名单，将其转为 RetryableToolResult，让框架重试。写工具不在 retry tools 中，因此不会自动重放，但仍经过预算与单次 timeout 包装。

## SharedModelBudgetMiddleware

每次模型 handler 调用前执行 budget.consume_model，子图使用同一 budget。这里计数框架可见的模型调用，不枚举 SDK 内部的网络重试。

## HealthSafetyMiddleware

从当前消息序列末尾寻找 HumanMessage；仅在主 Agent（delegation_depth=0）上检测有限中文紧急自述。规则寻找“我现在/我正在/突然出现/目前有/持续出现”后一定距离内的胸痛、呼吸困难、意识不清、大量出血，并排除同一分句近邻否定表达。
命中时发 guardrail.blocked 元数据，直接返回固定 ModelResponse/AIMessage，建议立即寻求急救；不再进入后续模型 handler。这只是有限句式规则，不是完整分诊算法，也不能证明其他表达都安全。

## 组装与验证

Lead 的中间件顺序让健康规则可以在模型预算和 provider 调用前短路；ToolBoundary 在外层把重试结束结果规范成 ToolResult。test_reliability 覆盖真实三次读取尝试、永久失败不重试、写结果未知、预算截断、单次超时取消、真实检索链注入失败以及紧急规则与 checkpoint/幂等回放一致性。

## 相关源码说明

- [backend/app/agent/budget.py](budget.py.md)
- [backend/app/agent/tool_middleware.py](tool_middleware.py.md)
- [backend/app/agents/lead_agent.py](../agents/lead_agent.py.md)
- [backend/tests/integration/test_reliability.py](../../tests/integration/test_reliability.py.md)

