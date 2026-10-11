# health_repository.py：健康记录与幂等回执

- 对应源码：`backend/app/persistence/health_repository.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/health_repository.py) · [目录说明](README.md)

## 结构与公开结果

RECORDS 将 metric/diet/exercise/document 映射为 ORM 类。public_row() 遍历实际列，排除 user_id，把 datetime 用 iso_utc 转成 Z 字符串；其他字段保留原值。这个函数同时被文档 Repository 复用。IdempotencyConflict 是专用异常，不携带原始健康数据。

## add() 的事务步骤

输入是已校验的 kind、可信 user_id、values、operation_key 和 payload_hash。

1. 按 user_id+operation_key 查询 WriteReceipt。
2. 同 key 不同 hash 抛 IdempotencyConflict；已有匹配回执直接返回原结果。
3. 插入健康行并 flush，以获得 id/default 字段；序列化公开结果。
4. 插入带 payload_hash 和 result 的 WriteReceipt，同一次 commit 提交。
5. 若并发插入撞唯一约束导致 IntegrityError，rollback 整笔事务，再读已提交回执；存在匹配回执则返回它，无回执则重新抛错误。

因此健康行与回执不会各提交一半，并发重复调用可得到相同记录 id。这里只处理数据库唯一冲突；超时/连接断开等提交结果不明的情况交给上层恢复策略，不能随意换 key 重试。

## query() 的过滤与排序

先选择 kind 对应 ORM，metric 用 measured_at、document 用 created_at，其余用 timestamp。where 总含 user_id；start/end 为闭区间；metric_type 仅用于 metric。按时间降序，再按 id 降序稳定排序，应用 limit，输出公开字典列表。

Repository 不验证 QueryInput.limit，也不自动判断 truncated；[HealthService](../services/health.py.md) 多取一条处理列表截断，或取 10001 条检查趋势容量。因此不能把 Repository 当作外部 HTTP 入口直接接收任意 kind/limit。

## 设计边界与测试

这里没有 update/delete、临床范围判定或营养推断。document 映射用于元数据查询，正常文档导入通过 KnowledgeRepository 管理索引生命周期。查询返回不含 user_id 是减少暴露，真正隔离来自 SQL。

[健康测试](../../tests/integration/test_health_tools.py.md) 验证四路并发去重、内容冲突、两用户隔离；[HTTP 测试](../../tests/integration/test_ui_api.py.md) 验证三类记录以及同 request_id 跨种类冲突。修改事务时必须保留“健康行+回执一起提交”和冲突后重新核对 hash 的行为。
