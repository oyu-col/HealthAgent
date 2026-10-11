# tools：模型可调用的显式业务入口

- 对应目录：`backend/app/tools/`
- 核对日期：2026-10-04
- 源码：[目录](../../../../backend/app/tools/)；上级：[app 说明](../README.md)

## 作用与设计目的

工具层把普通 Service 方法包装成 LangChain @tool，提供模型可理解的名称、说明和参数 schema。模型提出调用，真正的校验、授权来源、事务和结果结构由后端决定；工具不能直接访问数据库或自行接受 user_id。

- [health.py](health.py.md)：8 个结构化健康工具，包含 3 写入、4 查询、1 趋势。
- [knowledge.py](knowledge.py.md)：search_health_knowledge，提供第 9 个基础工具。
- [__init__.py](__init__.py.md)：说明显式注册，不进行自动扫描。

Lead 的委派工具在 agents 模块定义，不属于这里九个基础工具。三个专业 Agent 从基础工具中选择只读 allowlist，未自动拥有所有能力。

## 调用链和输入约束

模型参数 → Pydantic record/query → ToolRuntime 注入的 RunContext.user_id/operation_id → Service → Repository。ToolRuntime 为框架注入参数，不公开给模型填写身份。结果用 ToolResult.model_dump(mode=json) 形成统一观察：success/data/error_code/error_message/retryable。

写工具按业务请求身份与内容指纹生成 operation_key；它不依赖模型随机产生的 tool_call_id，避免同轮重复提案造成重复健康行。工具描述要求数据由用户明确提供，不猜食物量、营养或未知热量；这不是自动事实核验器，Service 也无法证明用户是否真的说过某个值。

## 可靠性边界

调用预算、只读重试、超时、无进展检测在 agent 中间件而非这些薄包装里实现。写工具不自行重试，不提供删除/覆盖健康事实能力。[健康集成测试](../../tests/integration/test_health_tools.py.md) 验证真实图—工具—数据库—观察链路及参数 schema 不暴露 user_id；[RAG 测试](../../tests/integration/test_rag.py.md) 验证检索工具证据。
