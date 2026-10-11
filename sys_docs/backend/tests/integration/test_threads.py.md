- 对应源码：`backend/tests/integration/test_threads.py`
- 核对日期：2026-10-04
- 阅读源码：[test_threads.py](../../../../backend/tests/integration/test_threads.py)
- 所属目录：[目录说明](README.md)

# 会话持久化、幂等、恢复与并发隔离测试

## 定位与测试方法

通过实际 FastAPI、临时 SQLite 和框架 checkpointer，证明跨应用实例的会话状态与业务写入一致。SpyChatModel/ToolChatModel 提供可控输出；不使用真实健康数据。

## 测试组和断言

### 重启续聊与请求幂等

test_history_survives_restart_and_requests_are_idempotent 首次不传 thread_id、带 request_id 创建会话；相同 ID/内容重发得到同答案和同 thread，同 ID 改内容为 409。关闭原 app 后用同配置创建第二个 app，再传原 thread_id 续聊，模型看见原用户内容与新内容，接口可见消息共 4 条且 pending=false。

### 写入后失败与原 checkpoint 恢复

FailAfterWrite 在收到 ToolMessage 后只失败一次，模拟健康记录已落库但最终模型回复失败。test_resume_checkpoint_after_write_without_duplicate 验证初次 500 带 thread_id，数据库已有且仅有 1 条指标。关闭原 app，使用全新模型和 saver 再调用 /resume 原 request_id，最终成功且仍只有 1 条，不靠旧内存状态去重。

### 归属与同会话并发

test_thread_owner_and_concurrent_runs 使用 alice/bob token 映射。Bob 读取或追加 Alice thread 都返回 404；Alice 对同 thread 并发提交两个请求，状态恰为 200 和 409，防止两个图同时写一个会话状态。

## 设计意义与范围

成功依据不仅是回答文本，还包括真实数据库行数、可见历史与跨实例恢复。重启在测试中由 lifespan 顺序结束/重建模拟，尚不是多进程故障注入；并发测试对应当前单 worker admission 设计，不证明多 worker 安全。

## 修改注意

改 ThreadService.prepare、回执主键、checkpoint message ID 或 fail/complete 顺序时应检查这些用例。不能通过清空数据库消除重复写，也不能用“新请求重问一遍”替代 resume 的语义。

## 相关源码说明

- [backend/app/services/threads.py](../../app/services/threads.py.md)
- [backend/app/api/threads.py](../../app/api/threads.py.md)
- [backend/app/api/chat.py](../../app/api/chat.py.md)
- [backend/tests/fakes.py](../fakes.py.md)
- [backend/tests/integration/test_replay_integrity.py](test_replay_integrity.py.md)

