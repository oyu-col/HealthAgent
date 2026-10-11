- 对应源码：`backend/app/agents/subagents.py`
- 核对日期：2026-10-04
- 阅读源码：[subagents.py](../../../../backend/app/agents/subagents.py)
- 所属目录：[目录说明](README.md)

# 受限专业子 Agent 与委派工具

## 定位与设计目的

通过一个 delegate_health_task 工具向 Lead 暴露三个无持久会话、只读、不可递归的专业子图。目的是复用框架执行机制进行范围明确的分析，同时保留身份、预算、证据和失败边界。

## 当前角色与允许工具

| 角色 | 工具集合 | 重点约束 |
| --- | --- | --- |
| nutrition | query_diet_records、search_health_knowledge | 分析已有饮食与证据，不补造份量或营养值。 |
| record | query_health_metrics、query_exercise_records、calculate_health_trend | 指标/运动/趋势仅作描述性分析。 |
| research | query_health_documents、search_health_knowledge | 回答必须关联实际引用和来源。 |
SPECIALISTS 的集合用于真正筛选工具，而不仅写进提示词。每个子图 checkpointer=False，使用 RunContext、共享模型预算、工具边界、读取重试、框架工具次数限制。

## 输入与结构化输出

工具参数 agent 是 nutrition/record/research 枚举，task 长度 1–3000；ToolRuntime 从服务端注入 context/config，不给模型暴露 user_id。
成功返回 ToolResult，其 data 为 SpecialistReport：agent、delegation_id、status=completed、summary（最多 6000 字符）、observations（最多 8 项）、truncated 和固定 notice。每项 SpecialistObservation 在 ToolResult 上增加 tool_name。completed 只代表图有终态答案，不保证 observation 全成功或结论医学正确。

## 真实委派流程

1. run 检查 delegation_depth 非零则拒绝递归；校验角色、空任务和长度。
2. 扣共享委派预算，生成 delegation_id。
3. dataclasses.replace 形成子 context：更换 agent_name、depth=1、delegation_id，重置重复观察字典；保留可信用户、时区、原业务标识、共享 budget 和 Trace sink。
4. 发 delegation.started；总子任务 timeout 包住 semaphore 等待和整个调用，所以排队也计入子任务时限。
5. 只给子图一条包含 task 的 HumanMessage，配置只转发 callbacks，另设子图步数、delegation run_id 和角色元数据。不传父消息历史、父 thread/checkpoint configurable 或任意模型指定配置。
6. 用 ainvoke(version="v1") 得到结果，经 extract_answer 验证，收集实际 ToolMessage 观察并返回报告。
7. finally 总是发 delegation.finished，包含安全角色/状态/错误码/耗时。

## 观察结果截断

summarize_observations 遍历 ToolMessage，跳过无法解析成 ToolResult 的消息。最多 8 项；单项序列化超过 6000 字符或累计超过 18000 时，用 omitted/reason 替代 data 并标记 truncated。summary 也截到 6000 字符。原状态不完整复制给 Lead，避免无限放大上下文。

## 错误、取消与共享保护

子任务超时/递归步数上限变成 subagent_timeout/subagent_step_limit ToolResult；未知异常变固定 subagent_error，不泄露原异常。AgentError 的 tool_limit、step_limit、delegation_limit、no_progress 会继续上抛，中止整个共享预算执行；其他已分类错误变受控子任务失败。CancelledError 保持取消语义，释放 semaphore 后原样抛出。
capacity 限制同一 SpecialistPool 同时执行数量；不是跨进程分布式队列。子图新建并不重置 budget；父委派工具自身也消耗工具尝试预算。子图不能写入健康事实，但读取工具仍可能按策略重试。

## 验证与修改注意

test_subagents 覆盖三角色、父历史不传、身份隔离、真实 observation 汇总、禁止写入与递归、共享限额、并发峰值和取消释放。扩大工具集合时必须检查是否仍只读；新增角色不能仅加提示词而忘记 allowlist 和 schema。

## 相关源码说明

- [backend/app/agents/lead_agent.py](lead_agent.py.md)
- [backend/app/agents/prompts.py](prompts.py.md)
- [backend/app/agent/context.py](../agent/context.py.md)
- [backend/app/agent/reliability.py](../agent/reliability.py.md)
- [backend/tests/integration/test_subagents.py](../../tests/integration/test_subagents.py.md)
- [backend/tests/integration/test_provider_transport.py](../../tests/integration/test_provider_transport.py.md)

