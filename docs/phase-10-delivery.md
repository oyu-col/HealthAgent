# Phase 10 — Trace / Observability

## Completed

- 通过 LangChain 公开 `AsyncCallbackHandler` 捕捉真实模型与工具调用，记录步骤标识、父步骤、耗时、调用结果状态；领域 hook 记录只读工具重试、子 Agent 委派和安全规则命中。
- `health.db` 独立 `execution_traces` 表保存受 owner 约束的执行摘要和事件。提供 `GET /api/traces` 分页 / thread 过滤和 `GET /api/traces/{trace_id}` 详情。
- 覆盖普通调用、SSE、checkpoint 恢复、取消和幂等结果回放；回放单独标为 `cached`，不虚构模型与工具步骤。
- 模型返回真实 `usage_metadata` 时累计 token；缺失时显示 `null`，部分已知时标 `complete=false`，不按字数估算 token。
- 开始先持久化 running 记录，终态保存后才返回权威回答。Trace 开始保存失败时拒绝运行；终态保存失败时返回安全的 `trace_unavailable`，可以使用已有 checkpoint 恢复，不宣称已成功保存追踪。
- 当前进程外终止留下的 running 记录，在下次启动改为 `interrupted`；不可恢复的调用计数、token 和耗时为未知，不填零。
- Lead SSE 增量按可信 `health_agent_name` 过滤，子 Agent 内部草稿不作为 Lead 回答直接输出。
- `/healthz` 阶段标记更新为 10；Phase 11 Benchmark 不包含在本次实现中。

## Files Changed

- `backend/app/observability/recorder.py`：回调收集、领域事件、元数据 allowlist、去重、token、事件上限。
- `backend/app/persistence/trace_repository.py`：独立 ORM 表、初始化、中断识别、owner 查询、保留上限。
- `backend/app/api/traces.py`：只读分页和详情接口。
- `backend/app/agent/runtime.py`：trace 生命周期、回调绑定、取消清理、Lead delta 隔离。
- `backend/app/main.py`：lifespan 注册 repository 和 API，接入 Phase 7–8 `settings`。
- `backend/app/api/chat.py`、`backend/app/api/stream.py`：缓存回放 trace。
- `backend/app/api/schemas.py`、阶段断言：Phase 10 标记。
- `backend/tests/integration/test_observability.py`、`backend/tests/unit/test_trace_recorder.py`：真实图调用、持久化、隔离、重试 / 委派、取消与失败验证。

## Design

Trace 是执行元数据，不是健康记录副本。仅保存服务端 trace / run / thread / request ID、任务类型和输入长度、预先允许的工具 / Agent 名称、固定错误码、调用状态、步骤标识、耗时和已报告的 token。Prompt、用户问题、回答、工具参数、工具返回数据、文档片段、异常文本、模型配置和凭据均不进入 trace。规范中 tool_arguments / tool_results 的诊断需求通过工具名称与成功 / 错误码表达，不另建敏感原文副本。

同次 Lead 与子 Agent 继承一个回调，依据 LangChain 模型 / 工具 run ID 去重；子 Agent 委派次数来自实际 `delegation.started` 领域事件，不从文本或工具名称猜测。独立的 `model_retries` 与 `tool_retries` 表示已观察到的重试；`retry_observation=framework_and_domain_hooks` 明示观察边界，OpenAI SDK 内部 HTTP 重试没有公开回调时不伪造精确次数。一次工具尝试的失败与 Agent 后续调整策略调用其他工具分别体现在步骤序列。

`total_steps` 定义为实际模型调用数加实际工具尝试数，不等同于 LangGraph 内部中间件节点数。token 对同一个模型 run ID 最多计一次；后到的 usage 回调允许补全数值而不重复创建模型步骤。成功仅表示 Agent 执行结束，不代表健康建议正确或工具调用均成功；工具失败后由 Lead 解释不足，也可能是正常的 completed 执行。

每次运行最多保存 400 个元数据事件，超出增加 `dropped_events` 并将 `capture_complete=false`。默认全库保留 1000 条、每用户 250 条 trace，先删除最旧的已结束记录，不逐出进行中的记录；容量不足时拒绝接受新的 trace。所有普通列表 / 详情 SQL 查询均带 owner 条件。Trace 查询不触发模型调用。

事件先在本次运行内存中累计，终态统一写入；进程崩溃可能只有开始摘要，重启会标为 interrupted，而非捏造完成。正常取消使用 shield 等待终态写入；模型 / 工具原始异常不会出现在错误响应或日志中。持久化发生故障时仅记录固定日志事件和服务端 trace / run ID。

## DeerFlow Reference

- `deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py`：参考 run-scoped trace ID、公开 LangChain callback 注入以及终态处理责任分离。
- `deer-flow/backend/packages/harness/deerflow/runtime/journal.py` 和 `runtime/AGENTS.md`：参考模型 / 工具生命周期、同一模型 run ID 的结束回调去重，以及 late usage 更新语义。
- 本项目采用本地 SQLite、有限元数据和一次终态写入，未复制 DeerFlow 的消息 journal、完整原文保存、队列桥、外部追踪服务和重连事件历史。

## Tests

2026-10-03 执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_observability.py tests/unit/test_trace_recorder.py tests/integration/test_streaming.py tests/unit/test_runtime.py
```

结果：**44 passed in 9.54s**。其中 Phase 10 新增 14 项测试覆盖：真实图 callback token=11/7/18、未知 token、持久化重启、两用户隔离、工具不保存原文、失败 / 恢复 / 缓存回放、普通取消和流式关闭、trace 开始和终态存储故障、事件上限、保留策略、重复 callback、真实子 Agent 委派、真实工具重试、Lead SSE 不泄露子 Agent 草稿。

实际委派验证为 4 次模型调用、2 次工具调用、1 次委派；一次瞬态读故障后成功验证为 2 次工具尝试、1 次工具重试、2 次模型调用。都是合成数据和注入测试模型上的实际框架执行，不是在线模型质量评测。

Ruff 针对新增和修改的 Phase 10 文件已通过。最终全后端、前端和真实 HTTP / 浏览器回归由汇总验证记录给出，不将本节局部测试结果写成全套结果。

独立复核补充：缓存回放时 Trace 存储失败不能将已完成请求回执降级或清空答案，完成回执现通过条件更新保持不可变；并发 Trace 准入在同一 worker 内从裁剪、计数到提交持有锁，防止突破容量。新增 8 项回归覆盖普通 / SSE 回放的 start / finish 存储故障、全局 / 用户并发容量、running 与已结束记录混合回收。先复现 5 项失败（其中上限 1 时曾接纳 7 项），修复后相关专项 27 项通过，最终新增文件 8 项通过。

## Known Issues

- 不接外部 tracing 平台；没有跨服务关联、后台事件持续 flush 或运行中详情增量。
- SDK 私有 HTTP 重试不可精确观察；未提供 usage 的模型 token 保持未知。运行中 trace 是开始快照，崩溃可能丢失尚未落盘的步骤。
- 当前单 worker / 单事件循环，与 Thread admission 和 SQLite checkpoint 部署约束一致。
- 保留上限是有限数量的摘要和事件，并非完整审计归档；trace 不替代健康事实、checkpoint 或 benchmark 真值。
- Trace 的 completed 表示图执行与 trace 写入完成；后续业务回执 / HTTP 传输故障仍由 Thread 恢复机制处理。

## Next Phase

Phase 11：建立 20–30 个 HealthAgent Domain Benchmark cases，依据数据库状态、证据、trace 与终止原因判定结果，并记录真实失败分析。本次没有提前生成 Benchmark 分数或宣称模型效果提升。
