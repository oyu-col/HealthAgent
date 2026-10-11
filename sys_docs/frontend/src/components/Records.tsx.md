# 身体指标、饮食和运动记录界面

- 对应源码：`frontend/src/components/Records.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/Records.tsx) · [本目录说明](README.md)

## 业务目的

页面展示真实结构化健康记录，并通过表单直接调用健康业务 API。此路径不依赖模型是否理解自然语言，fake 模式同样可以真实写入数据库。页面顶部是说明性文案，没有把合成统计值当作用户健康数据。

## Records 列表组件

输入是 token 和 session。kind 初始为 metric，可切换 diet/exercise；filter 是身体指标筛选；adding 决定是否打开表单。`useResource` 读取 `GET /api/records/{kind}?limit=100`，指标类型被选中时追加 metric_type。

响应是 `ToolResult<{records, truncated}>`：HTTP 请求成功并不等于业务成功，页面同时处理 resource.error 和 success=false 的 error_message。列表明确区分加载、错误、没有记录、有记录四种状态。truncated 为 true 时说明仅展示最近 100 条，当前没有分页、时间范围筛选或趋势图控件。

体重、静息心率、睡眠时长、步数分别映射 kg/bpm/hours/count 与图标。饮食显示食物、份量和餐次；运动显示项目、分钟和可选距离。时间使用 session.timezone 展示，缺少时间显示“时间未提供”，不会生成一个虚构时间。

## RecordForm：构造三类严格载荷

| 类型 | 提交字段 |
|---|---|
| metric | metric_type、数值 value、与类型绑定的 unit、measured_at |
| diet | food_name、amount、meal_type、timestamp |
| exercise | exercise_type、duration、timestamp、可空的 distance |

表单的 datetime-local 使用设备本地时区录入，经 `new Date(...).toISOString()` 转成带 Z 的时间；显示时再按工作区时区转换。默认时间由 localDateTime 提供。饮食没有自动估算热量；运动也没有自动填充卡路里。

体重和心率最小 0.01，睡眠范围 0–24，步数整数且不小于 0，运动时长 0.1–1440 分钟，距离不小于 0。文本字段有必填和长度约束。这些浏览器约束便于早期反馈，不能替代后端验证。

## 写入、幂等与异常

`operation` ref 保存序列化 payload 与 UUID。用户在同一已打开表单中重试完全相同记录，会沿用 request_id；更改载荷后生成新 ID。请求为 `POST /api/records/{kind}`，JSON 外层是 `{record, request_id}`，不会提交 user_id。

保存中关闭/取消按钮被阻止，成功时调用 onSaved 关闭表单并刷新列表；ToolResult.success=false 转成可见错误，失败时保留表单供重试。组件卸载会取消请求，但取消不能证明服务端未写入。幂等 ref 仅存在于当前表单生命周期，关闭重开不保留；最终去重由后端负责。

相关说明：[资源与时间 Hook](../lib/hooks.ts.md)、[API 请求](../lib/api.ts.md)、[共用弹窗](ui.tsx.md)、[表单浏览器验证](../../tests/e2e/workspace.spec.ts.md)。

