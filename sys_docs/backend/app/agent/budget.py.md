- 对应源码：`backend/app/agent/budget.py`
- 核对日期：2026-10-04
- 阅读源码：[budget.py](../../../../backend/app/agent/budget.py)
- 所属目录：[目录说明](README.md)

# 跨主图与子图的共享执行预算

## 定位与设计目的

ExecutionBudget 是单次已准入执行的内存计数器，防止子图或工具重试各自重新获得一份无限预算。它不是数据库配额、账号长期限额或 provider 账单统计器。

## 字段与方法

默认 max_tool_calls=12、max_model_calls=12、max_delegations=3；当前累计 tool_calls、model_calls、delegations、retries 初始为 0。实际创建时由 Settings 覆盖限制值。
consume_tool、consume_model、consume_delegation 都先判断“已用量是否达到上限”，达到即抛 AgentError，否则加 1。对应错误为 tool_limit、step_limit、delegation_limit，HTTP 状态均为 503。retries 没有独立 consume 方法，由重试中间件在第二次及以后物理尝试中累加。

## 调用关系与并发前提

RunContext.create 创建预算；SharedModelBudgetMiddleware 消耗模型预算；BoundedReadRetryMiddleware 消耗每次实际工具尝试；SpecialistPool.run 消耗委派次数。子上下文通过 dataclasses.replace 保留同一个 budget 对象，因此并行专业任务也共享限额。
consume 中无 await，在当前单事件循环下不会出现“读计数后暂停再增加”的协程竞态。此设计明确建立在单 worker/单事件循环之上，不能据此推导多进程全局限流能力。

## 状态与恢复边界

每次 admitted run 都有新的预算；沿原 request_id 恢复会新建一次执行上下文，不等于跨重启累计永久预算。LangGraph 的递归步数限制与这里的模型调用计数并存，不能把 graph step 和物理 SDK 网络重试都等同于 model_calls。

## 验证与修改注意

可靠性测试证明只读重试按每次尝试扣额；子 Agent 测试证明共享工具/模型/委派限额不能被子图重置。若将来引入线程/多 worker，必须重做原子性与集中配额，而不是仅调大默认值。

## 相关源码说明

- [backend/app/agent/context.py](context.py.md)
- [backend/app/agent/reliability.py](reliability.py.md)
- [backend/app/agents/subagents.py](../agents/subagents.py.md)
- [backend/tests/integration/test_reliability.py](../../tests/integration/test_reliability.py.md)
- [backend/tests/integration/test_subagents.py](../../tests/integration/test_subagents.py.md)

