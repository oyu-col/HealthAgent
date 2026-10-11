# test_observability.py：真实执行中的 Trace 行为验证

- 对应源码：`backend/tests/integration/test_observability.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/tests/integration/test_observability.py) · [测试目录](README.md)

## 测试目的与夹具

验证实际 LangGraph callbacks、领域 hook、Runtime 生命周期、SQLite Trace 和 HTTP/SSE 的协作。UsageModel 是本地注入模型，报告 usage=11/7/18；SpyChatModel、ToolChatModel、StreamingModel、DelegatingModel 模拟确定性行为。PrivateDraftModel 根据可信 delegation_depth 为子图生成 PRIVATE_CHILD_DRAFT、Lead 生成 PUBLIC_LEAD_ANSWER。

名称含 real 的测试表示运行真实框架/工具链，而不是调用真实在线 LLM；所有健康标记是合成的隐私探针。

## 持久化、usage 与用户隔离

- test_trace_persists_real_model_usage_without_health_text：对话完成后 Trace 为 completed，1 次模型、0 次工具，usage 精确为 11/7/18 且 complete=true、耗时非负、有 model.finished；SYNTHETIC_PRIVATE 不出现。重启后按 thread_id 列表仍能查到摘要，列表不含 events。
- test_trace_owner_isolation_and_unknown_tokens：Alice 可读自己的 Trace，Bob 详情 404/列表空，匿名 401；未报告 usage 时 total_tokens=None、complete=false。
- test_tool_trace_omits_arguments_and_results：真实 add_diet_record 工具执行，Trace 记录工具步骤，但 PRIVATE_FOOD/AMOUNT/HEALTH 标记均不出现。

## 故障、取消和缓存

- test_failure_resume_and_cached_replay_have_separate_honest_traces：模型异常的 Trace 为 failed/internal_error 且不泄露异常文字；修复模型后 resume 创建 task_kind=resume 且沿原 request_id；再回放产生 cached Trace，模型/工具调用均为 0，completed。
- test_cancelled_execution_is_persisted_and_stream_trace_is_completed：等待延迟模型真正启动后取消任务，CancelledError 向上传播，Trace cancelled；随后正常 SSE 有 run.completed，Trace completed 且一次模型调用。
- test_trace_storage_failure_prevents_untraceable_execution：Trace.start 故障映射 trace_unavailable，错误不泄露 PRIVATE，模型未被调用。
- test_terminal_trace_write_failure_does_not_return_success：Trace.finish 故障导致 HTTP 503，保留 running/capture_complete=false 开始快照；恢复存储后同请求 resume 可使用 checkpoint 缓存，task_kind=cached。
- test_closing_a_stream_persists_cancellation_without_final_success：获取第一个 message.delta 后 aclose 流，Trace cancelled，原输入不在 Trace 中。
- test_tool_timeout_trace_does_not_claim_missing_callbacks_were_captured：定义会被取消的合成只读工具，超时设为 0.05 秒并关闭重试；真实 create_agent/Runtime 返回标准 tool_timeout，工具 finally 确认收到取消。读取持久化 Trace，比较 tool.started 与 tool.finished 的 step_id 集合，要求 capture_complete 与实际配对一致。请求 completed 只表示最终回答已解释工具失败，不能据此断言回调全部收齐；若框架以后能正常发出结束回调，集合相等时此测试也允许完整。

这些断言保护“Trace 保存失败不能伪装完成”和“取消也需终态记录”；它们不证明整个业务写入已回滚，健康事实与 checkpoint 有独立事务。

## 委派、重试与增量隔离

test_real_delegation_callback_and_domain_events_are_not_double_counted 通过真实子图委派断言：subagent_calls=1、model_calls=4、tool_calls=2；delegation.started/finished 各一条且 delegation_id 相同、agent_name=record；model.started 的 Agent 集合为 health_lead_agent 与 record_agent。PRIVATE_ROOT_TASK 不进入 Trace。

test_real_tool_retries_are_distinct_from_model_calls_and_do_not_log_exceptions 定义一个第一次 TimeoutError、第二次成功的只读 query_health_metrics，关闭子 Agent、重试初始等待为 0。真实图成功后 Trace 为 tool_retries=1、model_retries=0、tool_calls=2、model_calls=2，原异常 PRIVATE_UPSTREAM_ERROR 不记录。

test_streaming_subagent_drafts_do_not_appear_as_lead_deltas 用 SSEDecoder 解帧，末帧 run.completed.answer=PUBLIC_LEAD_ANSWER，所有 message.delta 拼接也只等于该答案，PRIVATE_CHILD_DRAFT 不在响应。这验证可信 Agent 名过滤，不只是最终回答覆盖草稿。

## 关联、未覆盖范围与维护

实现见 [TraceRecorder](../../app/observability/recorder.py.md)、[TraceRepository](../../app/persistence/trace_repository.py.md)，并与 Runtime、SSE、子 Agent 和可靠性中间件协作。事件裁剪、晚到 usage 回调去重和保留策略还由 unit/test_trace_recorder.py 覆盖；历史完成回执及并发容量见 [test_replay_integrity.py](test_replay_integrity.py.md)。

该套用固定 usage 验证累计逻辑，不证明在线模型一定报告 token，也不精确观察 SDK 私有 HTTP 重试。没有医学准确率、建议安全性或模型效果评估。Phase 12 只修正完整性标记，不根据标准化 ToolMessage 猜测并补造框架结束回调；超时 Trace 仍可能明确显示不完整。

2026-10-11 已与 test_trace_recorder.py 联合运行：23 passed（8.16 秒），对应源码与测试 Ruff 检查通过。新增超时回归曾先在旧实现上失败：请求正常结束、dropped_events=0、工具只有 started 没有 finished，但 capture_complete 错报 true。修正后该路径保留真实事件并标记 false。
