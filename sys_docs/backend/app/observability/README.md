# observability：不保存健康原文的运行观测

- 对应目录：`backend/app/observability/`
- 核对日期：2026-10-11
- 源码：[目录](../../../../backend/app/observability/)；上级：[app 说明](../README.md)

## 功能定位

该目录收集一次执行中的模型、工具、委派、重试和规则事件，用于解释调用过程和失败原因。它与业务健康事实、聊天 checkpoint 分开：Trace 不应成为问题、答案、文档片段或工具参数的另一个副本。

[recorder.py](recorder.py.md) 实现公开 LangChain AsyncCallbackHandler，接收框架回调和项目领域 hook；[__init__.py](__init__.py.md) 仅提供包说明。持久化在 [TraceRepository](../persistence/trace_repository.py.md)，HTTP 查询在 api/traces，生命周期在 agent/runtime，前端 Trace 弹窗消费查询结果。

## 一次 Trace 的流程

Runtime 建立 TraceRecorder → 先持久化 running 摘要 → callbacks 按模型/工具 run_id 收集并去重 → 领域 emit 记录委派和重试 → 生成终态 summary → Repository 一次写入事件。子图共享根 recorder，避免重新累计另一份运行。

运行中事件主要在内存，进程崩溃可能丢失未落盘事件；启动恢复把旧 running 标 interrupted，并将未知计数置 null。当前没有持续事件 flush 或外部 tracing 服务。

## 数据语义

total_steps 是模型调用数+工具尝试数，不是图内部每个节点；completed 表示执行结束与 Trace 写入完成，不代表医疗建议正确或每个工具都成功。usage 仅采用模型报告，不按文本字数估算。工具重试和模型重试是已观察事件数，SDK 内部网络重试可能不可见。

单次默认最多 400 个事件，超出计 dropped_events 并标 capture_complete=false；全库/owner 保留策略由 Repository 控制。

Phase 12 进一步要求每个已开始的模型/工具 run_id 都有真实结束回调，才允许终态 capture_complete=true。同名并发调用和重试 attempt 分别配对，不以名称或累计数量代替。超时取消可能造成“请求已完成、工具结束回调缺失”，此时保留实际事件并标完整性为 false，不补造成功或失败事件。这一修改提高观测标记的可信度，尚未消除框架取消路径的回调缺口。

[Trace 集成测试](../../tests/integration/test_observability.py.md) 使用合成健康字符串验证不会泄露，同时覆盖真实图回调、超时与持久化；[单元测试](../../tests/unit/test_trace_recorder.py.md) 检查配对、去重、裁剪与合法零调用。2026-10-11 两文件共 23 项测试通过，属于离线框架行为验证，不是在线医疗效果评测。
