- 对应源码：`backend/tests/unit/test_trace_recorder.py`
- 核对日期：2026-10-11
- 阅读源码：[test_trace_recorder.py](../../../../backend/tests/unit/test_trace_recorder.py)
- 所属目录：[目录说明](README.md)

# Trace 去重、脱敏、容量与重启行为测试

## 定位与测试层次

文件位于 unit，但保留策略测试实际使用临时 SQLite 和 TraceRepository，因此同时包含小范围持久化集成验证。它关心可观测性数据是否诚实、有限且不含健康原文。

## 具体用例

| 测试 | 关键动作与意义 |
| --- | --- |
| test_terminal_capture_is_incomplete_when_started_callback_has_no_end | 模型/工具分别只触发 started，不触发结束回调；与 completed、cancelled、timeout 三种终态组合成 6 项参数化用例，要求即使 dropped_events=0，capture_complete 仍为 false，且 summary 不得修改事件列表补造结束。 |
| test_capture_matches_each_parallel_tool_attempt_including_failed_attempt | 两个不同 run_id 调用同名工具，先结束第二个，完整性仍为 false；第一个收到真实 on_tool_error 后才为 true，重复错误回调不重复记结束。验证按 attempt 配对，而非工具名称、最后一个结果或请求终态推断。 |
| test_no_callback_execution_can_be_complete_only_when_terminal | 缓存/规则回复允许零模型、零工具；running 时完整性 false，真实终态无裁剪时为 true，避免把合法短路路径误判不完整。 |
| test_callback_dedup_and_late_usage_do_not_duplicate_steps | 同一 run_id 重复触发 model start/end，先无 usage 再补 3 输入+2 输出=5 token，之后重复及零值回调；断言仅 1 次模型调用、总 token 仍为 5、事件只有 start/end 两条、不含合成 PRIVATE 内容。 |
| test_custom_events_are_allowlisted_and_bounded | max_events=2 时注入 tool.retry、delegation.started、model.retry 和未知事件；断言保留 2 条、丢弃 1 条、capture_complete=false；汇总重试和子 Agent 次数仍累计；args/prompt/task/secret 和不允许错误码不落事件。 |
| test_retention_prunes_old_finished_traces_and_restart_marks_running | 全局/每用户容量均设 2，插入 3 条已完成 Trace，最早条被清理；再留 2 条 running，重新 initialize 后标为 interrupted/process_interrupted，latency_ms 为 None、capture_complete=false。 |

## 数据与错误语义

输入模型内容完全是合成标记，测试故意把敏感字段塞进回调，验证记录器只保存白名单。未知 usage 和重启丢失事件不能被填成“0 次/0 token 的完整执行”。
保留策略用例在相同数据库会话内重新 initialize 模拟重启初始化逻辑，并不是强杀真实服务进程；应如实理解其覆盖范围。

Phase 12 新增配对测试前，旧 summary 只判断终态及事件裁剪；漏掉结束回调也会返回 capture_complete=true。新断言先在旧实现上失败，再以开始/结束 run_id 集合相等修复。不要求所有调用成功，仅要求已开始的调用都有真实结束观测。

## 修改注意

新增 Trace 事件、统计字段、token 合并策略或保留清理规则时同步调整断言。不能为让测试通过而把缺失 usage 统一填零，也不能把所有 callback kwargs 存起来。

2026-10-11 与 test_observability.py 联合执行：`python -m pytest tests/unit/test_trace_recorder.py tests/integration/test_observability.py -q`，共 23 passed（8.16 秒）；对应源码与测试 Ruff 检查通过。新测试在修复前的定向运行得到 8 failed、1 passed，其中 1 个失败来自真实工具超时集成用例，证明错误确实存在。

## 相关源码说明

- [backend/app/observability/recorder.py](../../app/observability/recorder.py.md)
- [backend/app/persistence/trace_repository.py](../../app/persistence/trace_repository.py.md)
- [backend/app/persistence/database.py](../../app/persistence/database.py.md)
- [backend/tests/integration/test_observability.py](../integration/test_observability.py.md)

