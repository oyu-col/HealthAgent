- 对应源码：`backend/tests/unit/test_runtime.py`
- 核对日期：2026-10-04
- 阅读源码：[test_runtime.py](../../../../backend/tests/unit/test_runtime.py)
- 所属目录：[目录说明](README.md)

# Runtime 真实图调用、输出过滤与错误边界测试

## 定位与测试策略

通过 SpyChatModel 和真实 build_lead_agent/StateGraph 验证执行封装，重点是控制流与安全边界，不是模型医学能力。provider_error 是供本文件及其他测试复用的合成 SDK 异常工厂。

## 具体测试组

- **真实图与 context**：test_real_graph_and_trusted_context 验证实际回答、只调用一次模型、SystemMessage 等于公共提示词、最后为 HumanMessage、传入可信 RunContext，未配置时 graph.checkpointer 为 None。
- **可见答案提取**：参数化检查普通字符串去空白、多个 text 块拼接、忽略 reasoning/图片；拒绝空状态、非列表/空消息、末尾非 AI、仅隐藏内容、截断 finish_reason 和待调用工具消息。不能用历史旧 AI 内容充当当前结果。
- **异常分类脱敏**：覆盖 SDK 超时、连接、429/503、400/401、协议错误和未知异常，断言 AgentError 的 code/status，响应/日志不含 LEAK 标记和健康输入；每种仅一次模型调用，未偷偷加应用层重试或 fake 回退。
- **总时限与取消**：慢模型触发 timeout 后确实收到取消；外部 task.cancel 继续抛 CancelledError，而非正常文本答案。
- **框架步骤限制**：构建会循环增长的真实 StateGraph，使 Runtime 映射 GraphRecursionError 为 step_limit。
- **输入预检**：空白和过长文本不进入模型。
- **外部追踪隔离**：即使环境开启 LANGSMITH_TRACING 并带合成 key，模型内观察到 tracing flag 仍为 False。

## 输入输出与资源

settings 来自共享 fixture，SpyChatModel 记录见过的消息、context、取消和追踪标志。provider_error 使用 example.invalid 与固定合成敏感标记，从不访问公网。

## 覆盖边界与修改注意

本文件不测试 SQLite Thread 幂等、完整 SSE HTTP 帧或真实在线 provider，这些在集成测试/显式 live 测试分别覆盖。改变 Runtime 返回格式、SDK 异常层次或 LangGraph 调用 version 时应优先运行本文件，再验证相关集成链。本说明不宣称本次重新运行通过。

## 相关源码说明

- [backend/app/agent/runtime.py](../../app/agent/runtime.py.md)
- [backend/app/agent/context.py](../../app/agent/context.py.md)
- [backend/app/agents/lead_agent.py](../../app/agents/lead_agent.py.md)
- [backend/tests/fakes.py](../fakes.py.md)
- [backend/tests/integration/test_streaming.py](../integration/test_streaming.py.md)

