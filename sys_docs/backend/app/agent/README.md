- 对应目录：`backend/app/agent/`
- 核对日期：2026-10-04
- 实际目录：[agent/](../../../../backend/app/agent/)
- 上级说明：[目录说明](../README.md)

# 执行机制与可靠性层

## 定位：解决“如何运行”

本目录给框架执行增加可信上下文、预算、错误和收尾，不定义健康领域角色，也不重写模型/工具循环。角色定义位于同级 agents；HTTP 入口位于 api。

## 执行链

ThreadService 建立 RunContext → Runtime 进入 execution/Trace/总超时 → 已编译图运行 → 模型中间件检查紧急规则和共享模型预算 → 工具边界包裹有界读取重试/单次超时/框架限额 → 工具进入 Service。Runtime 从最终状态提取可见答案，并在成功对外前提交 Trace。

## 文件间协作

context 把服务端 user_id、时区、请求与 Trace 标识传给工具；budget 对象由主图/子图共享；reliability 负责哪些失败可自动重试以及每次实际尝试扣额；tool_middleware 负责规范化错误和相同调用三次无进展停止；errors 提供可公开错误类型；runtime 把框架/SDK 异常映射到统一结果。

## 状态与设计取舍

预算和观察指纹只存在单次 admitted run 内存；健康事实和幂等回执不在这里存。请求取消保持取消，不能转换为正常回答；Trace 收尾尽力在取消期间完成。总执行时限、单工具时限、子任务时限、图递归上限和共享调用预算是互补限制。
只读瞬态故障能有界自动重试，写结果未知则要求先查询核对。该层目前以单 worker/单事件循环为并发前提，不提供分布式 admission。

## 隐私与错误边界

不记录输入、答案、完整工具参数或 provider 原始异常；Graph 运行关闭无关外部 LangSmith tracing。上下文数据不可提升为系统授权，AgentError 类本身也不会自动脱敏任意字符串。

## 阅读顺序与测试

建议 runtime → context/budget → reliability → tool_middleware → errors。test_runtime 关注真实图边界；test_reliability、test_streaming、test_subagents、test_observability 验证跨层行为。修改中间件顺序必须回看真实组装代码，而非只看类名。

## 文件导航

- [__init__.py](__init__.py.md)：执行机制包入口。
- [budget.py](budget.py.md)：跨主图与子图的共享执行预算。
- [context.py](context.py.md)：可信执行上下文 RunContext。
- [errors.py](errors.py.md)：可公开的执行错误类型。
- [runtime.py](runtime.py.md)：HealthAgent 执行入口、终态答案与 Trace 收尾。
- [reliability.py](reliability.py.md)：有界读取重试、共享模型预算与紧急规则。
- [tool_middleware.py](tool_middleware.py.md)：工具返回规范化与重复无进展保护。

