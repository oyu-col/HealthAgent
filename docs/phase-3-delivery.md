# Phase 3 — Thread / Checkpoint

## Completed

会话创建、列表、归属校验、历史查询、同会话继续对话、请求幂等与恢复接口已完成。应用重启后可读取历史，并通过原生 checkpoint 恢复失败节点。

## Files Changed

新增 ThreadRecord / ChatRun、`persistence/thread_repository.py`、`services/threads.py`、`api/threads.py`；修改 chat 请求 / 响应、runtime 和 lifespan。新增 `tests/integration/test_threads.py`，锁定 `langgraph-checkpoint-sqlite==3.1.1`。

## Design

应用 owns thread_id / user_id / request_id 元数据，官方 AsyncSqliteSaver 独立管理 `checkpoints.db`。相同 request_id 重放返回已完成结果；内容冲突返回 409。以 request_id 作为 HumanMessage id 及工具幂等操作边界。未完成会话拒绝追加新请求，恢复使用 `ainvoke(None)` 继续待执行节点，尚无初始 checkpoint 时重送原输入。同一进程同一 thread 只允许一个 run，其他会话可并发。应用 lifespan 关闭 saver / SQL engine / 模型客户端。

## DeerFlow Reference

阅读 `runtime/checkpointer/async_provider.py`、`persistence/thread_meta/model.py` 及 Phase 0 已定位的 SQL owner 查询。借鉴业务 metadata 与框架状态分离、checkpointer 生命周期管理；没有复制 Gateway、分布式 worker、checkpoint cache 或自建消息存储循环。

## Tests

2026-10-03：完整离线测试 **79 passed / 1 skipped**，15.66 秒。覆盖同 thread 多轮、应用重建后的历史、请求重放冲突、跨用户 404、并发 409，以及写入成功而最终模型失败后重启恢复，确认没有重复健康记录。

## Known Issues

当前使用单进程 admission，部署必须 `--workers 1`；多进程需要 Phase 8 之后扩展跨进程租约。SQLite 文件含私人健康数据与会话，应受操作系统权限和备份策略保护。该阶段恢复指正常 graph checkpoint 继续执行，未新增人工审批 / interrupt UI。

## Next Phase

Phase 4：框架原生流转换为 SSE，提供增量客户端及取消、错误验证。
