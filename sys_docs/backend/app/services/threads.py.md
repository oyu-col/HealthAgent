# threads.py：会话准入、恢复与用户可见状态

- 对应源码：`backend/app/services/threads.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/services/threads.py) · [目录说明](README.md)

## 设计目的

ThreadService 在 HTTP 请求与 LangGraph Runtime 之间管理“谁能运行哪个会话”和“这次请求是否已执行过”。聊天消息与图节点状态只属于 checkpointer；本服务通过 [ThreadRepository](../persistence/thread_repository.py.md) 管理 owner、active_request_id 和 ChatRun 回执，避免自己复制一套图状态。

PreparedRun 保存 context、message（恢复节点时可为 None）、cached_answer。进程内 _admission 锁串行化准入检查，_active 集合标识本进程执行中的 thread，**只支持单 worker**。

## 用户可见元数据

owned() 按 owner/thread 联合查询，不存在或不属于当前用户统一 thread_not_found/404。metadata() 读取 checkpoint 与活动回执：

- title 取首条 HumanMessage，尚无 checkpoint 时取活动请求 message；去控制字符、归一空白，最多 48 字符，无内容为“新对话”。
- status 为 running、failed、interrupted、idle；running 来自本进程 _active，失败/中断取决于未完成回执。
- pending 只表示 checkpoint.snapshot.next 非空。
- can_resume 根据未完成回执且当前不运行判断；如果图已结束、对应请求的人类消息已在 checkpoint，但无法提取合法答案，则禁止恢复。

因此 pending=false 不等于无需恢复：图完成后业务回执写入失败仍可利用最终答案完成回执。state() 仅返回 HumanMessage 和不含 tool_calls 的合法 AI 最终文本，过滤工具内部载荷与空/无效 AI 结果。list() 最近最多 100 条，每条读取图状态，当前没有批量 checkpoint 查询优化。

## prepare() 的主要决策顺序

1. 缺省 request_id 时生成 UUID；以 user_id/request_id 查询历史回执。
2. 已有回执而请求 thread 或 message 变化，返回 request_conflict/409；resume 指向不存在请求时 run_not_found/404。
3. 验证已有会话归属或新建会话；正在执行返回 thread_busy/409。
4. 未完成旧回执不是当前 active_request_id，返回 stale_run；新请求遇到活动未完成回执，返回 resume_required。
5. 新请求建立 ChatRun 并更新活动标识；创建新的可信 RunContext。
6. 已完成回执提供 cached_answer。若 checkpoint 最新 HumanMessage.id 等于 request_id 且存在待运行节点，将 message=None 继续图，避免重复追加用户消息。
7. 同请求图已结束则提取答案作为缓存；没有合法答案返回 resume_unavailable/409。
8. 把 thread 放入 _active，yield PreparedRun；finally 无论成功失败都移出。

complete()/fail() 分别委托 Repository 写 completed/failed 回执，run_id 来自本次 context。已完成回执的不可变保护在 Repository，而非依赖调用方不再调用 fail。

## 事务边界与恢复意义

Thread 创建、请求回执、checkpoint、Trace 和健康写入是不同事务。不能声称一次对话具有数据库全局回滚；设计依靠稳定 request_id、工具幂等 key 与 checkpoint 衔接恢复。缓存回放可以创建新执行 Trace，但不应覆盖原已完成回执的答案或原 run_id。

[UI API 测试](../../tests/integration/test_ui_api.py.md) 覆盖 title、running/interrupted、完成图但回执失败、无效终态不可恢复；[回放完整性测试](../../tests/integration/test_replay_integrity.py.md) 覆盖历史回执在 Trace 故障下不可降级。改变锁或状态逻辑前应保持这些行为；多 worker 需要新的跨进程协调机制。
