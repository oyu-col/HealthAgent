# health.py：结构化健康业务服务

- 对应源码：`backend/app/services/health.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/services/health.py) · [目录说明](README.md)

## 职责与调用关系

HealthService 接收可信 user_id，封装指标、饮食、运动写入以及四类记录查询和指标趋势。它由 [健康工具](../tools/health.py.md) 和 records HTTP API 共同调用，持久化只通过 [HealthRepository](../persistence/health_repository.py.md)。它不调用模型、不估算营养、不提供诊断，也没有删除/覆盖健康事实接口。

## add()：可恢复的写入

输入为 kind、user_id、record、operation_key。INPUTS 只允许 metric/diet/exercise 对应的 [Pydantic 模型](../domain/schemas.py.md)。

1. model_validate 再次验证 record。
2. 使用 kind + 排序后的 JSON 对原始已验证输入做 SHA256。
3. 在完成哈希以后，才为缺省时间补当前 UTC；显式时间通过 utc_naive() 转 UTC 并去掉 tzinfo。
4. Repository 用 operation_key 和 payload_hash 写业务记录及回执。
5. 成功返回 ToolResult.ok(记录)，同操作标识参数变化映射为 idempotency_conflict。

先算哈希再补时间十分关键：原请求未传时间时，两次重试的当前时刻不同，但应命中同一回执。operation_key 本身由调用方生成，Agent 与 UI 使用不同生成策略；Service 不把相同内容的所有历史记录永久合并。

## query() 与 trend()

query() 使用 QueryInput 的时间范围、类型和 limit；Repository 多取一条，即 limit+1，返回 data={records,truncated}。truncated 明确告知前端/Agent 列表不完整。

trend() 独立取同类指标最多 10001 条：超过 10000 返回 range_too_large，少于两条返回 insufficient_data。有效结果含 metric_type、unit、count、mean、min、max、first、last、change 和“描述性统计，不构成医学诊断”。Repository 按时间倒序，因此 first=rows[-1]、last=rows[0]，change=最新值−最早值。它不按日补齐、不加权、不做回归预测；同一时间戳的稳定次序由 UUID 排序决定。

## 隔离、事务和异常

所有查询显式传 user_id；公开结果不包含 owner。Service 只专门捕获 IdempotencyConflict，其他数据库错误交给上层处理。单条记录与回执同事务由 Repository 保证，趋势是一次读取，不锁定未来新增记录。

## 验证与修改注意

[健康工具测试](../../tests/integration/test_health_tools.py.md) 覆盖 UTC 转换、同 key 重试/冲突、跨用户隔离、并发去重、营养未知和趋势 -1；[UI API 测试](../../tests/integration/test_ui_api.py.md) 覆盖真实表单链路。新增 kind 必须同步 INPUTS、Repository RECORDS、时间字段选择、工具和 HTTP 校验，不应把 unknown calories 自动变成 0。
