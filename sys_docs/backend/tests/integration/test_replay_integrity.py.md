# test_replay_integrity.py：历史回执不可变与 Trace 容量并发

- 对应源码：`backend/tests/integration/test_replay_integrity.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/tests/integration/test_replay_integrity.py) · [测试目录](README.md)

## 为什么独立成文件

这组回归聚焦两个容易被正常成功路径掩盖的问题：回放历史请求时新的 Trace 故障不得毁掉原完成回执；多个请求同时检查容量时不能都认为仍有空位。测试基于真实应用/SQLite 和故障注入，不使用真实模型或真实健康信息。

## 已完成历史请求的回放

test_failed_trace_replay_preserves_completed_historical_receipt 以 streaming=False/True 和 failure_at=start/finish 两维参数化：

1. 完成第一条请求并保存 answer、run_id，再在同一 thread 完成第二条请求。
2. monkeypatch Trace start 或 finish 抛 PRIVATE_STORAGE_FAILURE。
3. 回放第一条业务 request_id；普通 HTTP 应 503/trace_unavailable，SSE 最后应 run.failed 且对应错误码。
4. 直接读第一条 ChatRun，断言仍 completed，答案和原 run_id 不变。
5. 恢复 Trace 方法后再次回放，返回原答案，没有新增模型调用。
6. 当前会话 active_request_id 仍为第二条请求，status=idle。

它保护 [ThreadRepository.finish](../../app/persistence/thread_repository.py.md) 的条件更新，防止新 Trace 的失败路径把旧已完成回执清空；也保护 [ThreadService](../../app/services/threads.py.md) 不把历史回放当作新的活动业务请求。

## 并发容量严格生效

test_concurrent_trace_admission_cannot_exceed_running_capacity 分全局上限/owner 上限两种场景，构造 12 个 recorder 并 asyncio.gather 同时 start。全局模式每个 owner 不同而 max_total=1；owner 模式同一用户且 max_per_user=1。两种都断言恰好 1 个成功、11 个 trace_capacity，库中总计 1 条。

这是当前单 worker 内的并发验证，证明 TraceRepository 准入锁必须覆盖计数、插入直到 commit；不证明跨进程部署安全。

## 只回收终态容量

test_mixed_running_and_finished_traces_reclaim_only_terminal_capacity 参数化全局/owner 上限，依次种入 running、completed、running，再 start 新运行。断言仍保留前两条 running 和新 running，旧 completed 不可再查询，错误为 trace_not_found。owner 模式另建其他用户已完成记录并断言未被当前用户裁剪误删。

对应 [TraceRepository._prune/start](../../app/persistence/trace_repository.py.md)。测试关注保留对象集合，不是 SQLite 文件压缩或磁盘空间释放。

## 维护边界

此文件是工程回归集，既不评估医疗回答，也不等于压力/负载 Benchmark。修改 completed 不可变条件、Trace 锁范围、裁剪排序或 owner 条件时应保持这些断言。本次只编写文档，没有运行本文件。
