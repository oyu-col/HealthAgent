# recorder.py：白名单 Trace 回调记录器

- 对应源码：`backend/app/observability/recorder.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/app/observability/recorder.py) · [目录说明](README.md)

## 设计目的与状态

TraceRecorder 继承 AsyncCallbackHandler，run_inline=True、raise_error=False。一个根运行持有一个 recorder，模型/工具 run_id 分别作为 model_runs/tool_runs 键；ended_models/ended_tools 防重复结束事件；usage 按模型 run_id 累积；events 在内存保存。构造时记录可信 context、task_kind、model_mode、输入字符数、UTC 开始时间和 perf_counter。

不保留 callback 的 messages、input_str、工具返回 data 或原异常对象。工具输出仅临时解析标准 envelope 的 success/error_code，不保存 payload。

## 白名单与清洗函数

TOOL_NAMES、AGENT_NAMES、ERROR_CODES 是可记录枚举，未知名称/错误值变 unknown。CUSTOM_EVENTS 仅允许 tool.retry、model.retry、delegation.started、delegation.finished、guardrail.blocked。

safe_error()/safe_name() 只接受白名单字符串；token_counts() 要求 input_tokens/output_tokens/total_tokens 都是 type(x) is int，且 0–10^12，合法时只返回这三项。它不校验 total 等于 input+output，不猜测缺失字段。

emit() 逐键清洗：工具/Agent 名称按集合筛选；计数夹到 0–10000；有限耗时夹到 0–10^8；布尔值要求真实 bool；delegation_id 必须能解析 UUID；status 只能 completed/failed/cancelled。任意自由文本键被丢弃。计数随已观察事件增加，再调用 append。

## 框架回调如何记录

- on_chat_model_start：同 run_id 仅一次 model.started，保留 step_id、parent_step_id、可信 metadata.health_agent_name。
- on_llm_end：读取 generation.message.usage_metadata；同 run_id 如后到 usage.total_tokens 更大则补全替换，不重复 model.finished。
- on_llm_error：同一次模型运行最多结束一次，只写 success=false 和耗时，不写 error 原文。
- on_tool_start：固定工具名、父步骤、Agent 名，绝不保存 input_str。
- on_tool_end：ToolMessage 字符串若是标准 JSON 结果 envelope，读取 success 及安全错误码；否则以 output.status 判断。不会保存原始结果内容。
- on_tool_error：固定失败状态、safe_error(error.code)、耗时。
- on_retry：仅能定位到已知 tool/model run_id 时记录对应 retry；未知 run 不凭空归类。

## 事件上限与 summary()

append 为事件增加从 1 开始的 seq 和 elapsed_ms。events 达默认 MAX_EVENTS=400 后停止增加正文，递增 dropped_events；模型/工具/重试的内存计数仍持续更新，不等于停止执行。

summary(outcome) 输出 trace/run/thread/request 标识、任务类型、输入长度、模式、开始/结束时间、状态、终止码、耗时、调用与重试计数、total_steps、token_usage、event_count、dropped_events、capture_complete。

outcome=running 尚无终态时间；completed 对应 completed；cancelled 对应 cancelled；其他终止原因对应 failed。total_steps=len(model_runs)+len(tool_runs)。没有任何 usage 则 token 数量为 None；部分已知会求已知和，但 complete=false；只有存在模型调用且每次都有合法 usage 时 complete=true。

Phase 12 修正了 capture_complete 的判断：请求处于终态、dropped_events=0、model_runs 的 run_id 集合与 ended_models 相等、tool_runs 的 run_id 集合与 ended_tools 相等，四项同时成立才为 true。比较使用每次框架调用的 run_id，不能只比较工具名或总数；同名并发工具、重试的不同 attempt 必须各自配对。on_llm_error/on_tool_error 收到真实结束回调时也算“已完整观测”，不要求执行成功。

这是“已开始调用的结束是否被观测”的完整性标记。模型或工具在取消时可能没有产生结束回调，即使 Runtime 最终正常返回“工具超时”的解释，capture_complete 仍为 false。summary 不会据此补造 tool.finished 或推测工具成功/失败。合法的规则直接回复、缓存回复可以没有任何模型/工具调用；其两个集合都为空，终态且未裁剪时仍可为 true。SDK 私有调用是否全部可见不由本字段保证。

## 数据流、持久化和边界

Runtime 把 summary/events 交 [TraceRepository](../persistence/trace_repository.py.md) 持久化。记录器本身没有数据库事务，也不读取用户配置密钥。callback run_id/parent_run_id 由框架提供；输入字数仍是元数据，文档/健康原文不进入 Trace。

[Trace 集成测试](../../tests/integration/test_observability.py.md) 验证模型 usage=11/7/18、无 usage 的 null、工具隐私、委派不双计、只读重试与子 Agent 草稿隔离，并通过真实超时路径检查缺失结束回调时不能宣称完整。[Trace 单元测试](../../tests/unit/test_trace_recorder.py.md) 检查上限、回调去重、模型/工具未配对、并发同名 attempt 和零调用缓存。

2026-10-11 已运行这两个测试文件：23 passed（8.16 秒），对应源码与测试 Ruff 检查通过。没有在线模型调用。新工具/错误码需同步白名单，否则将显示 unknown；不得为了诊断方便记录任意工具 arguments 或异常字符串。
