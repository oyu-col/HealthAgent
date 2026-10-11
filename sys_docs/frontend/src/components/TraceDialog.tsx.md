# 执行 Trace 指标和事件时间线

- 对应源码：`frontend/src/components/TraceDialog.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/TraceDialog.tsx) · [本目录说明](README.md)

## 使用场景与接口

Chat 在获得 traceId 后打开此组件。props 为 traceId、token、onClose。组件使用 wide 版 Dialog 和 `useResource<Trace>` 请求 `GET /api/traces/{encodeURIComponent(traceId)}`，读取失败时提供重试。没有在本地从文字片段反推调用次数，也不绕过服务端检查 Trace 所属用户。

## 数据结构和展示

文件内定义 TraceEvent 与 Trace 类型，没有放进共享 types.ts。TraceEvent 包含 seq、event、elapsed_ms，以及可选 name、agent_name、success、error_code、latency_ms、attempt。Trace 汇总包括状态、终止原因、总耗时、模型/工具/子 Agent 次数、可观测重试、total_steps、task_kind、采集完整性、丢弃事件数、Token 用量及事件数组。

当前界面展示总耗时、模型/工具调用数、专业委派数、可观测重试数；total_steps、Token 输入输出分项、事件 attempt/latency_ms 虽在类型里声明，但尚未逐项渲染。时间线右侧展示的是相对运行开始的 elapsed_ms，不是该事件自身耗时。

## 对未知值的处理

- duration(null) 显示“—”；不足 1000 ms 用整数毫秒，其余用两位小数秒。
- 计数 null 显示“—”，不能转换为 0。
- token_usage.complete=false 时显示“不可完整观测”，即使部分 Token 字段有值也不伪称完整总量。
- termination_reason=null 显示“尚未结束”。
- capture_complete=false 或 dropped_events>0 时提醒缺失部分不能视为未发生。

这些处理使 Trace 适合故障调查：不知道和没有发生是不同结论。

## 时间线语义与边界

事件名称覆盖模型开始/结束、工具开始/结束、模型/工具重试、专业委派、保护规则、运行开始/结束和缓存命中；未知名字原样显示。success===false 明示“失败”并用失败色圆点；true 明示成功；未提供 success 的事件不补造结果。

task_kind 为 cached 显示复用持久化结果，为 resume 显示恢复执行，其余为新一轮对话。界面说明仅展示执行元数据、SDK 内部重试可能不可见。本组件没有自动轮询、完整 Trace 列表、导出按钮或模型思维链面板；当前作用是查看单次 Trace。

相关说明：[Chat 入口](Chat.tsx.md)、[共用 Dialog](ui.tsx.md)、[未知值与失败事件浏览器测试](../../tests/e2e/workspace.spec.ts.md)。

