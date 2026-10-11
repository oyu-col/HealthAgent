# fakes.py：保留真实图执行的可控模型

- 对应源码：`backend/tests/fakes.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[fakes.py](../../../backend/tests/fakes.py)

## SpyChatModel

继承 LangChain BaseChatModel，支持 bind_tools，返回自身以适配 create_agent 装配。同步 _generate 记录 messages，可抛注入 failure，否则查找最后 HumanMessage 并返回“收到：…”的 AIMessage/ChatResult。

异步 _agenerate 记录 get_runtime().context 和当前 tracing enabled 状态，可 await delay，用于触发超时/取消；CancelledError 时将 _cancelled 置真后继续抛出。PrivateAttr 的 _seen、_contexts、_tracing_flags 让测试断言可信上下文、历史隔离和外部追踪关闭，不把这些观察字段放进模型配置。

## ToolChatModel

继承 SpyChatModel，增加 tool_name/arguments。bind_tools 收集每个工具公开 tool_call_schema 的 JSON schema，便于验证 user_id 等可信字段没有暴露给模型。

当最后消息尚不是 ToolMessage 时，它返回固定工具调用（id=test-call）；收到 ToolMessage 后将真实 observation 作为最终 AIMessage。这样测试能走真实工具节点、数据库和结果封装，又不要求模型理解自然语言。

## 使用边界

这里的模型属于测试替身；应用默认演示模型在 [models/demo.py](../app/models/demo.py.md)，二者不能混淆。固定工具 id 只为受控测试设计，不应复制为生产幂等策略。测试可观察的私有属性用于断言，不提供用户接口，也不代表医学知识推理能力。
