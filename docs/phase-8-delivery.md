# Phase 8 — Reliability

## Completed

基于已有总超时、LangGraph recursion limit、ToolCallLimitMiddleware、重复无进展检测、可信身份和写入幂等补齐以下能力：

- 使用框架 ToolRetryMiddleware，仅对 allowlist 只读工具的明确瞬态失败重试。
- 工具单次超时；每次真实尝试、包括重试，消耗 Lead / 子 Agent 共享预算。
- 明确区分自动重试、Agent 修改策略、写入结果不确定以及不可恢复会话。
- 对有限的明确中文紧急自述直接返回寻求急救的提示，跳过模型；不提供诊断。
- 重试、委派与守卫事件通过 RunContext event_sink 交给 Phase 10 Trace。

## Files Changed

- `backend/app/agent/reliability.py`：框架读取重试、瞬态分类、尝试超时、共享模型预算、有限紧急自述守卫。
- `backend/app/agent/budget.py`、`context.py`：同运行共享预算与安全事件 sink。
- `backend/app/agent/tool_middleware.py`：保留标准 ToolResult / 无进展检测，预算控制信号直接传播，写入不确定状态明确返回。
- `backend/app/services/knowledge.py`：仅在 search 的只读边界区分 embedding / 检索瞬态失败；摄取写入没有自动重放。
- `backend/app/config.py`、`agents/lead_agent.py`、`agents/prompts.py`：有界配置与装配。
- `backend/tests/integration/test_reliability.py`、`test_subagents.py`、`tests/unit/test_config.py`：行为回归。

## Design

默认读取最多重试 2 次，即初次调用加 2 次重试。框架负责指数退避和 jitter：初始等待 0.1 秒、倍数 2、最大等待 2 秒。允许的失败包括 timeout、连接失败 / 重置、HTTP 429 / 5xx 和 SQLite busy / locked；参数错误、401、未知异常、索引容量限制等不会因“失败”而自动重试。

工具默认单次超时 10 秒；委派本身采用子任务的超时，整个运行仍受既有总超时控制。缺失参数不进入工具函数，不发生重复执行。取消和 LangGraph 控制信号直接传播。重复同工具 / 参数 / 观测 3 次会停止无进展循环；本阶段保留该已验证机制，没有再造 Agent while 循环。

健康写工具不在重试 allowlist 中。发生可能已提交的超时 / 存储错误时，返回 `write_outcome_unknown`，`retryable=false`，要求先核对已有记录。已有 Service / Repository 事务回执和 operation_id 幂等仍生效；不能用“幂等”作为盲目重放所有未知写失败的理由。

检索服务原来把所有异常折叠为 retrieval_failed；现在只有明确瞬态错误返回 `retrieval_unavailable` 且 retryable=true。框架重试器重新执行实际 Retriever，而非将同一失败文本当成新结果。文档摄取、索引发布和上传写入没有加入自动重试。

共享模型调用预算计算框架调用次数，SDK 内部网络重试由原有 `MODEL_MAX_RETRIES` 单独限制；Trace 不声称观测到了 SDK 未公开的每次内部请求。每次自动工具重试发送 `tool.retry` 及 attempt，Agent 重新规划则表现为新的模型 / 工具调用，二者分开。

紧急守卫只识别有限的明确现在时中文自述，例如“我现在胸痛并且呼吸困难”，返回建议联系当地急救或身边人协助就医的固定提示，并保留“不能进行诊断”的能力边界。否定语句的测试不触发该规则。框架保存这个最终回答；SSE、checkpoint 历史和幂等重放一致。

## DeerFlow Reference

阅读 `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`，借鉴统一工具失败出口并保持 GraphBubbleUp 控制流。阅读 `subagents/capacity.py` 与 `agents/middlewares/subagent_limit_middleware.py`，借鉴有限资源与取消回收。

重试直接采用已安装 LangChain 的 `ToolRetryMiddleware`，并核对 [官方预置 Middleware 文档](https://docs.langchain.com/oss/python/langchain/middleware/built-in#tool-retry)。HealthAgent 只添加领域读取 allowlist、瞬态分类、每次尝试预算和安全错误转换，未复制 DeerFlow 的完整运行基础设施。

## Tests

实际执行的最终专项回归为 **51 passed，7.76 秒**（`test_subagents.py`、`test_reliability.py`、`test_config.py`）。此前与已有健康工具、RAG 和真实 SDK MockTransport 的扩展回归为 **67 passed，14.30 秒**。相关新增 / 修改文件 Ruff 检查通过。

覆盖：Timeout / 429 / 5xx / 连接重置读取成功重试、永久错误不重试、缺参不执行、工具超时取消及重试耗尽、写超时仅一次执行、共享预算不能被重试 / 子图绕过、有界配置校验。真实 KnowledgeService → ScopedVectorRetriever → SQLite 链路注入一次 embedding ConnectError，第二次返回真实 citation；测试先失败、分类修复后通过。

紧急守卫验证了模型不被调用、无诊断表述、否定语句不触发，以及 HTTP SSE 最终回答、checkpoint 历史、同 request_id 重放一致。既有健康工具 / RAG / 幂等验证继续通过。没有进行真实医疗效果评测。

## Known Issues

- 紧急守卫是小范围规则，不是完整医疗分诊、语义安全分类器或诊断系统；不保证覆盖改写、引用、其他语言或所有高风险情况。提示约束不能代替真实模型安全评测。
- 不能通过读重试修复永久参数错误、损坏索引或缺失证据；这些必须由 Agent 澄清或调整策略。
- 工具预算在当前单事件循环内原子预留，不是跨 worker 或跨恢复的持久配额。
- 无效终态 checkpoint 且无待执行节点时，can_resume=false；显式恢复返回 409 `resume_unavailable`，用户需新建会话重试。
- SDK 内部模型 / embedding 重试仍遵循现有配置，Trace 中只报告实际可观测的框架事件，不虚构内部尝试次数。

## Next Phase

Phase 9 将现有 UI 与专业分析 / 可靠性状态衔接；Phase 10 增加真实 Trace / Observability。不会将此阶段的合成回归测试称为 Phase 11 Domain Benchmark。
