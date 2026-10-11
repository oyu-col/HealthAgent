# trace_repository.py：有限保留的本地执行记录

- 对应源码：`backend/app/persistence/trace_repository.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/trace_repository.py) · [目录说明](README.md)

## 模型与责任

TraceBase 是独立 DeclarativeBase；TraceRecord 对应 health.db/execution_traces，run_id 主键，trace_id、user_id、thread_id、started_at、status 建索引，summary/events 使用 JSON。它与健康事实模型分离，仍共用业务数据库 session 工厂。记录内容由 [TraceRecorder](../observability/recorder.py.md) 先做白名单净化，Repository 不二次扫描 JSON 中的健康原文。

TraceRepository 默认全局 max_total=1000、每用户 max_per_user=250，并持有进程内准入锁。这个上限是记录数量，不是文件字节配额。

## initialize() 与中断诚实性

启动时创建 TraceBase 表。当前单 worker 部署下，残留 running 行被认为属于此前进程，改为 interrupted、termination_reason=process_interrupted；finished_at/latency 设 None，capture_complete=false；模型/工具/子 Agent/重试/总步骤以及 token 数量设未知 None。

这是因为事件先在运行内存累计、终态才统一写入，旧的开始快照不能代表实际执行零次。initialize 不重建丢失事件，也不恢复 Agent。

## start()：裁剪、容量预留和写入

在 _admission 锁与 session.begin 同时覆盖的范围内：

1. _prune 先按用户、再按全库上限，删除最旧的非 running 记录，为新运行腾一格。
2. 重新计数；如果仅剩 running 导致仍满，抛 trace_capacity/503，不驱逐正在运行的记录。
3. 将开始 summary 和空 events 写入 running 行，started_at 转 UTC 无时区。
4. 事务提交后释放准入锁。

锁跨越裁剪、计数、插入和提交，防止 SQLite deferred transaction 下多请求同时通过容量检查。它不支持跨 worker 协调。

## finish()、查询和授权

finish 以 owner+run_id 更新状态、summary 和完整 events，在一个事务内提交；不是恰好更新一行则抛 trace_unavailable/503。list 以 owner 必选过滤，可选 thread_id，按 started_at/run_id 倒序，应用 limit/offset，仅返回 summary；get 按 owner+trace_id 取最近记录，返回 summary+events，不存在统一 trace_not_found/404。

普通查询不能跨用户读 Trace。分页参数上限由 API 校验，Repository 不再次约束任意 limit。Trace 存储故障与健康记录/checkpoint 不是同一回滚边界，Runtime 决定失败时怎样对外响应。

## 验证和实际限制

[Trace 集成测试](../../tests/integration/test_observability.py.md) 验证重启、owner、未知 token、存储故障与恢复；[回放/容量测试](../../tests/integration/test_replay_integrity.py.md) 验证 12 路竞争时容量 1 只接受 1 个，以及只裁剪已结束记录。当前没有连续事件 flush、外部 tracing、长期审计归档和多进程锁；不可把保留策略描述成完整历史保存。
