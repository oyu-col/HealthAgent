# thread_repository.py：会话归属与请求回执

- 对应源码：`backend/app/persistence/thread_repository.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/thread_repository.py) · [目录说明](README.md)

## 作用与存储范围

ThreadRepository 管理 health.db 中 ThreadRecord 和 ChatRun；完整消息序列和 LangGraph 待运行节点由 checkpoint 管理。这里保存请求原文 message、最终 answer、状态和标识，不能将本表当作无敏感信息的日志。

## 方法

| 方法 | 行为与返回 |
| --- | --- |
| create(user_id) | 创建 ThreadRecord，commit 后返回 ORM 行 |
| get(user_id,thread_id) | owner+thread 联合查询，不存在返回 None |
| list(user_id) | 该用户最新 100 个 thread，created_at 倒序 |
| get_run(user_id,request_id) | 联合主键查询 ChatRun |
| create_run(...) | 创建 pending ChatRun，同时更新该 owner/thread 的 active_request_id，同事务提交 |
| finish(...status,run_id,answer) | owner+request_id 条件更新，且只允许原 status != completed 的行被更新 |

create_run 假设 ThreadService 已校验归属且准入互斥；它不自行处理 thread=None 或多个同时创建相同 request_id 的应用逻辑。不能绕过 Service 把 Repository 直接暴露为 API。

## 完成回执不可变的原因

finish 的 status != completed 条件非常重要。已完成历史请求再次回放时会建立新 Trace；如果新 Trace 保存失败，上层可能尝试标记失败。条件更新使这种故障不能清空原答案、降级 completed 或替换原 run_id。它也不会把历史回放设置成当前活动请求。

已完成回执后续调用 finish 是无修改的幂等操作；该函数不检查更新行数、也不返回更新结果，是否找到请求的正常前置校验由 ThreadService 处理。

## 独立事务与测试

ChatRun 回执不是 checkpoint 的原子组成部分。图完成但回执失败时，ThreadService 可读 checkpoint 答案补写回执；健康工具已提交写入也不会被回执失败回滚。

[回放完整性测试](../../tests/integration/test_replay_integrity.py.md) 交叉覆盖普通/SSE、Trace start/finish 故障，断言历史状态、答案、run_id 不变，后续活动 request_id 不被覆盖；[UI 元数据测试](../../tests/integration/test_ui_api.py.md) 覆盖图完成后的恢复。修改 finish 条件前应把这些语义作为回归边界。
