# test_health_tools.py：工具到真实数据库的集成验证

- 对应源码：`backend/tests/integration/test_health_tools.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/tests/integration/test_health_tools.py) · [测试目录](README.md)

## 测试目的与环境

验证实际 LangGraph 工具循环、Pydantic 参数、健康 Service/Repository 与临时 SQLite 之间能正确协作。通过 create_app、真实 lifespan 和 httpx.ASGITransport 访问本机进程内 HTTP；模型使用 tests.fakes.ToolChatModel 或本文件 RepeatingToolModel，不向真实 provider 发送健康信息。

RepeatingToolModel 每次返回同名同参数但不同 call id 的工具调用，用于稳定复现无进展循环。它保存看到的消息供断言，属于测试观测，不是生产 Trace 的日志策略。

## 逐项覆盖和断言

| 测试 | 行为与关键断言 |
| --- | --- |
| test_repeat_observations_stop_without_unbounded_tool_calls | max_steps 放宽到 50，模型反复查询；HTTP 503/no_progress，model._seen 恰为 3，证明更早的重复观察保护阻止无限调用 |
| test_agent_tool_database_observation_answer | 模型调用 add_health_metric 写合成 70kg；answer 的 ToolResult.success=true，数据库有 70，+08:00 的 08:00 存为 00:00Z，模型经历调用与读取观察两次，工具 schema 不含 user_id |
| test_idempotent_writes_and_owner_filter | Alice 同 operation_key 两次返回同记录 id，只有一条；Bob 查询为空 |
| test_invalid_metric_rejected | 参数化覆盖负体重、lb 错单位、NaN、非整数步数、无时区时间；均抛 ValidationError |
| test_invalid_tool_arguments_are_safe_structured_observation | 模型给负值和 SECRET 单位；观察为 validation_error、retryable=false，HTTP 文本不包含 SECRET |
| test_credentials_determine_identity | token 模式匿名 401；Bob token 加伪造 X-User-ID=alice 仍无法读到 Alice 指标 |
| test_diet_exercise_trend_and_concurrent_deduplication | 饮食未知 nutrition_info 为 None，运动分钟保存；4 路同 key 指标写入去重；改值沿原 key 产生 idempotency_conflict；两个独立时间体重 70→69 趋势 count=2/change=-1，Bob 返回 insufficient_data |

## 对应设计边界

测试关注 [health_tools](../../app/tools/health.py.md) → [HealthService](../../app/services/health.py.md) → [HealthRepository](../../app/persistence/health_repository.py.md)，以及 [输入契约](../../app/domain/schemas.py.md)。幂等用相同请求/操作身份，不代表系统能自动判断两个不同自然语言请求是否同一个真实事件。

## 如何解读结果与维护

这些是合成数据的工程集成测试，既不衡量医学建议正确率，也不证明真实模型一定选择正确工具。测试直接检查数据库和固定结构，比仅断言回复含某句话更能验证事实持久化。

新增指标、幂等策略或工具名称时，要更新对应工具 schema、数据状态和安全错误断言。NaN 等非法值在领域校验层测试，身份攻击在 HTTP 层测试，二者不能互相替代。本次编写说明仅阅读源码，没有重新运行测试；历史执行结果以 docs 阶段验收记录为准。
