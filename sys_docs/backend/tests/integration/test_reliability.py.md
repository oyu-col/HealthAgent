- 对应源码：`backend/tests/integration/test_reliability.py`
- 核对日期：2026-10-04
- 阅读源码：[test_reliability.py](../../../../backend/tests/integration/test_reliability.py)
- 所属目录：[目录说明](README.md)

# 重试、预算、超时、紧急规则的行为测试

## 目的与测试方法

使用真实 create_agent 图和可注入合成工具，在工具物理调用次数、预算、事件、数据库/检索证据层面验证可靠性。这里的工具异常是故意注入的测试数据，不代表当前线上故障。

## 具体测试组

- **瞬态只读自动重试**：参数化 TimeoutError、429、503、httpx.ReadError；前两次失败第三次成功。断言实际 3 次调用、tool_calls=3、retries=2、两个 tool.retry，事件不含 SECRET。
- **未知写入结果不重放**：写工具直接抛超时，断言仅调用 1 次，write_outcome_unknown、retryable=false。
- **缺失参数不执行**：工具 required_limit 未提供，得到 validation_error，真正工具调用 0 次、重试 0 次。
- **共享预算截断重试**：max_tool_calls=2、工具持续超时，最终 tool_limit，真实调用恰好 2 次。
- **紧急规则短路**：明确“我现在胸痛并且呼吸困难”返回急救提示且模型从未调用；否定表达会正常进入模型。
- **永久只读失败**：ValueError 和合成 provider 401 不自动重试，错误不泄露 SECRET。
- **单工具 timeout 真实取消**：慢读取每次等待 60 秒，但配置 0.01 秒、允许 1 次重试，断言 2 次实际调用都被取消，最终 tool_timeout。
- **真实检索链恢复**：先摄取合成文档，再将 embedding.aembed_query 的第一次调用替换为 ConnectError；最终检索引用真实已入库 document_id，embedding 共 2 次，budget.retries=1。
- **规则与持久化一致性**：紧急请求走 SSE 后，用相同 request_id 普通接口回放，答案一致；历史恰为用户+固定急救回复，状态 idle、不可恢复，模型始终未调用。

## 设计意义与边界

既验证“重试了多少次”，也验证“哪些绝不能重试”；使用真实检索服务的用例避免仅测试一个孤立 decorator。紧急用例证明有限规则与图/回执兼容，不是临床分诊覆盖或医学安全评测。
模型 SDK 内部重试未由这些工具计数断言穷尽；工具重试、框架模型调用、Agent 改策略是三层不同现象。

## 维护注意

变更 READ_TOOLS、TRANSIENT_CODES、错误分类或中间件顺序后，应检查所有组而不只 happy path。不要把未知写入超时改为自动重试来“提高成功率”，这可能产生重复健康事实。

## 相关源码说明

- [backend/app/agent/reliability.py](../../app/agent/reliability.py.md)
- [backend/app/agent/tool_middleware.py](../../app/agent/tool_middleware.py.md)
- [backend/app/agent/budget.py](../../app/agent/budget.py.md)
- [backend/app/agents/lead_agent.py](../../app/agents/lead_agent.py.md)
- [backend/app/services/knowledge.py](../../app/services/knowledge.py.md)

