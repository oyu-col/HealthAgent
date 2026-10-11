# Phase 7 — Multi-Agent

## Completed

Lead Agent 现有 9 个健康工具继续处理简单查询和记录；新增 `delegate_health_task(agent, task)`，将复杂只读分析交给 NutritionAgent、RecordAgent 或 ResearchAgent，再由 Lead 根据结构化结果汇总。默认启用，可通过 `HEALTH_AGENT_SUBAGENTS_ENABLED=false` 关闭委派。

三个专业 Agent 均以 LangChain `create_agent` 构建，采用显式只读工具 allowlist。NutritionAgent 查询饮食与证据，RecordAgent 查询指标 / 运动并计算趋势，ResearchAgent 查询文档元数据与检索证据。子 Agent 没有保存、删除、覆盖或继续委派的工具。

## Files Changed

- `backend/app/agents/subagents.py`：专业 Agent 注册、隔离调用、并发准入、委派工具与 `SpecialistReport`。
- `backend/app/agents/lead_agent.py`、`prompts.py`：Lead 装配和委派 / 汇总约束。
- `backend/app/agent/context.py`、`budget.py`、`config.py`：可信身份、共享预算和有界配置。
- `backend/tests/integration/test_subagents.py`：实际 LangGraph / SQLite 集成验证。
- `backend/tests/integration/test_provider_transport.py`：真实 ChatOpenAI SDK 的 10 个工具 schema 验证。
- 应用工厂通过 `build_lead_agent(..., settings=resolved_settings)` 接线；Trace 的关联事件由 Phase 10 集成。

## Design

调用链为 `Lead → delegate_health_task → scoped create_agent → read tools → observations → Lead`。只向子图传必要的任务文本，不传父会话历史；任务作为 HumanMessage 数据，不能修改系统指令或用户授权。可信 `user_id`、时区、operation_id 从服务端 RunContext 继承，模型工具参数不包含这些授权字段。

子图设置 `checkpointer=False`，没有独立持久会话，不向父 checkpoint 写入子图 HumanMessage 或中间模型消息。父图仍保存委派工具的最终结果。恢复未完成委派时可以重新执行只读子任务；不会因此重复写健康事实。

默认最多同时执行 2 个子任务、每次 run 最多 3 次委派、单次含排队时间最长 20 秒、子图 recursion limit 为 8。Lead / 子图共享工具尝试数与模型调用数；默认工具尝试上限 12，物理读取重试也消耗预算，子图不能获得一套新的无限预算。全请求总超时仍由 Runtime 管理。取消会向子图传播并释放并发名额。

专业结果使用 Pydantic `SpecialistReport`：agent、delegation_id、status、summary、observations、truncated、notice。observations 来自实际 ToolMessage，而不是子模型自行声明的工具结果；单条 / 总量有界，超出时明确省略。`completed` 仅表示执行结束，不能当作健康结论正确或所有工具成功的证据。Lead 必须核对 observations、引用及失败状态。

## DeerFlow Reference

已阅读参考仓库中的：

- `backend/packages/harness/deerflow/subagents/config.py`：按专业 Agent 限定工具、禁止递归委派。
- `subagents/executor.py`：`create_agent`、独立 HumanMessage 输入、`checkpointer=False`、结构化执行状态。
- `subagents/capacity.py`：并发名额、超时、取消后的名额回收。
- `agents/middlewares/subagent_limit_middleware.py`：单次 run 委派数量上限。
- `tools/builtins/task_tool.py`：Lead 通过工具委派并接收子任务结果。

HealthAgent 不复制 DeerFlow 的跨线程执行器、后台轮询、任务批次、沙箱与复杂任务登记系统；在同一事件循环中使用 bounded semaphore 和原生 graph invocation，适合当前单 worker 部署。框架接口也核对了 [LangChain Subagents 文档](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)。

## Tests

实际执行：Phase 7/8 新增集成测试首轮 **12 passed**；加入真实检索重试及已有健康工具 / RAG / SDK / 配置回归后 **67 passed**；最后扩充共享模型 / 委派预算、连接重置和缺参测试，专项 `test_subagents.py + test_reliability.py + test_config.py` 为 **51 passed，7.76 秒**。相关文件 Ruff 检查通过。

Phase 7 具体覆盖：三个角色实际委派、Lead 汇总、另一用户记录与文档不可见、当前用户真实 citation、父历史不传给子图、父可见历史没有子图消息、子图写操作被拒绝、递归拒绝、共享工具 / 模型 / 委派预算、并发上限、超时及取消回收。SDK 测试确认新增工具 schema，不包含 user_id 授权参数。

这些测试使用确定性测试模型、合成数据及真实框架 / 本地数据库。未执行真实 provider 的多 Agent 规划质量或医学领域 Benchmark，不宣称任务成功率提升。

## Known Issues

- 默认 fake 模型仍是回显适配器，不会自主规划工具或委派；专业 Agent 的规划需配置支持 tool calling 的真实模型。
- 子任务只有只读分析能力，写入继续由 Lead 的显式健康工具处理。
- 并发准入与共享预算属于一次已准入的运行，服务重启 / 显式恢复会建立新的运行预算；它不是跨恢复累计的配额系统。
- 截断后的 observations 必须按 truncated / omitted 标记处理，不能被当作全量数据。
- 仍为单 worker / SQLite；没有引入跨进程后台子任务、持久任务队列或生产鉴权体系。

## Next Phase

Phase 8 完成只读瞬态重试、工具超时、共享预算、结构化失败及健康场景守卫，详见 [Phase 8 交付](phase-8-delivery.md)。
