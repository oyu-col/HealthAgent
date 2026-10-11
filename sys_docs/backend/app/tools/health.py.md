# health.py：八个健康工具与写入身份

- 对应源码：`backend/app/tools/health.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/tools/health.py) · [目录说明](README.md)

## 工厂和注册

health_tools(service) 在函数内部定义 @tool，并返回固定列表，由 Lead 构建代码显式注册或筛选给子 Agent。模块导入没有网络请求、数据库初始化或工具自动发现。

| 工具 | 模型输入 | 调用 Service |
| --- | --- | --- |
| add_health_metric | record:MetricInput | add(metric,…) |
| add_diet_record | record:DietInput | add(diet,…) |
| add_exercise_record | record:ExerciseInput | add(exercise,…) |
| query_health_metrics | 可选 query:QueryInput | query(metric,…) |
| query_diet_records | 可选 query | query(diet,…) |
| query_exercise_records | 可选 query | query(exercise,…) |
| query_health_documents | 可选 query | query(document,…) |
| calculate_health_trend | metric_type + 可选 query | trend(…) |

所有工具还接收框架注入的 ToolRuntime[RunContext]，user_id 从 runtime.context 取，模型看不到可用来冒充其他 owner 的身份字段。可选 query=None 时创建默认 QueryInput。

## 写入幂等键的构造

内部 add(kind,record,runtime) 对 record.model_dump(mode=json) 使用排序键、保留中文的 JSON 序列化。fingerprint=SHA256(kind+payload)，operation_key=SHA256(context.operation_id+fingerprint)。

这使同一业务请求中、相同内容但不同 tool_call_id 的重复写提案命中同回执；不同业务请求仍可保存内容相同的独立记录。kind 参与指纹，避免不同记录类型混淆。Service 还独立计算 payload_hash 并验证回执冲突，不能仅依靠模型调用 id。

当 record 未给时间时，其 None 参与稳定指纹；实际当前时间在 Service 补入。若模型重新提案改变了值或显式时间，指纹也会变化；去重机制不是自然语言层面的“同一事件”判断。

## 结果、责任分配与限制

每个工具将 Service 的 ToolResult 转普通 JSON 字典；不吞异常、不补造结果、不直接 commit。输入校验错误由框架/项目工具中间件安全转观察。工具说明限定用户明确给出的数据和单位，但没有独立语义证据验证，真实模型提取质量仍需评测。

文档查询仅返回元数据/状态，全文搜索由 [knowledge.py](knowledge.py.md)；趋势计算由 [HealthService](../services/health.py.md) 从数据库计算，不让模型自行对截断列表做全量统计。

[集成测试](../../tests/integration/test_health_tools.py.md) 断言工具 schema 不含 user_id、记录按 UTC 入库、非法参数不泄露 SECRET、模型能读取真实 ToolResult，并触发重复无进展停止。更改名称还需同步子 Agent allowlist、重试策略和 Trace 工具白名单。
