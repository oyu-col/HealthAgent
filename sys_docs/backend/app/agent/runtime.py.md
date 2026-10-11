- 对应源码：`backend/app/agent/runtime.py`
- 核对日期：2026-10-04
- 阅读源码：[runtime.py](../../../../backend/app/agent/runtime.py)
- 所属目录：[目录说明](README.md)

# HealthAgent 执行入口、终态答案与 Trace 收尾

## 定位与设计目的

HealthAgentRuntime 包装已编译的 LangGraph 图，统一输入检查、总时限、公开错误、执行日志和持久化 Trace。真正的模型→工具→模型循环由框架完成；Runtime 不自建 while 循环。

## 关键方法

| 方法 | 作用 |
| --- | --- |
| extract_answer(state) | 从 v1 dict 状态的最后一条 AIMessage 取可见终态文字。 |
| ainvoke(message, context) | 普通或恢复执行入口，进入 execution 后调用图。 |
| astream(message, context) | 读取 v2 多模态流并产出项目内部事件。 |
| execution(...) | 异步上下文管理器，拥有总时限、Trace 与异常归一化。 |
| record_cached(context) | 为已完成请求的回执重放建立 cached Trace，不调用模型/工具。 |
| graph_config(context) | 注入递归限制、run_id、角色元数据、回调和可选 thread_id。 |
| graph_input(message, context) | 新消息生成带 operation_id 的 HumanMessage；恢复返回 None。 |

## 普通执行流程

ainvoke 拒绝空白或超过配置限制的输入，message=None 则表示恢复。execution 建立 TraceRecorder 并先调用 traces.start；成功后以 replace 给上下文注入只接受元数据的 sink。图调用显式选择 ainvoke(version="v1")，传公开 context 与 config；得到状态后 extract_answer 校验终值。
Trace.start 失败会在模型执行前返回 trace_unavailable/503。execution 使用 tracing_context(enabled=False)，防止机器上无关 LangSmith 环境变量自动把健康上下文发到远程追踪服务。

## 终态答案规则

state 必须是 Mapping，messages 必须是非空列表；只接受最后一条 AIMessage。仍带 tool_calls、invalid_tool_calls 或 finish_reason=length/content_filter 时拒绝。字符串首尾去空白；列表只拼接字符串和 type=text 的 text 块，忽略 reasoning/图片等。去空白后为空也拒绝，不能回退到历史中的旧答案。

## 流式执行流程

调用 graph.astream(version="v2", stream_mode=["messages","values","custom"])。values 保存最后状态；messages 仅转发 model 节点、角色为当前 Lead 且无 tool_calls 的可见文本；custom 仅接受 tool.started/tool.finished。专业子图的文字不会作为主助手回答直接流出。
迭代完后从最后 values 状态提取答案，离开 execution、完成 Trace 保存，才发内部 answer 事件。HTTP 层再保存线程完成回执并生成 run.completed。模型中间文本可能来自不同轮次，最终答案必须以该终态为准。

## 错误、超时和取消

- 请求超时或 APITimeoutError → timeout/504。
- 图递归限制 → step_limit/503；框架工具调用上限 → tool_limit/503。
- provider 连接错误、429 或 5xx → provider_unavailable/503；其余 HTTP 拒绝或 SDK 协议错误 → provider_error/502。
- 已分类 AgentError 保留原码；未知 Exception → 固定 internal_error/500。
- CancelledError 和 GeneratorExit 记录 cancelled 后重新抛出，不能转换成正常回答。
execution 和普通 _invoke_graph 均施加配置总时限；图流以 aclosing 保证关闭。日志仅记录 trace/run、终止原因和耗时，不写输入、答案、身份、密钥或原始 provider 异常。

## Trace 完成的特殊边界

finally 移除活跃 recorder，并创建独立任务调用 traces.finish，再 shield 等待。取消到达时仍等待保存任务收尾。终态 Trace 保存失败会记录脱敏日志；若业务本来完成则转 trace_unavailable/503，要求检查原请求并恢复。已发生的业务写入/checkpoint 不因此回滚；若原本就失败，则保留原始失败原因而不覆盖为 Trace 错误。

## 关联测试与修改注意

test_runtime 覆盖真实图、可见块、错误映射、总超时、取消、步骤预算和关闭外部追踪；test_streaming 覆盖流式事件和清理；test_observability/test_replay_integrity 覆盖 Trace 与回执恢复。升级 LangGraph 时必须同时验证 v1 dict 和 v2 StreamPart 语义，不能靠旧示例猜返回形状。

## 相关源码说明

- [backend/app/agents/lead_agent.py](../agents/lead_agent.py.md)
- [backend/app/agent/context.py](context.py.md)
- [backend/app/observability/recorder.py](../observability/recorder.py.md)
- [backend/app/api/chat.py](../api/chat.py.md)
- [backend/app/api/stream.py](../api/stream.py.md)
- [backend/tests/unit/test_runtime.py](../../tests/unit/test_runtime.py.md)
- [backend/tests/integration/test_observability.py](../../tests/integration/test_observability.py.md)
- [backend/tests/integration/test_replay_integrity.py](../../tests/integration/test_replay_integrity.py.md)

