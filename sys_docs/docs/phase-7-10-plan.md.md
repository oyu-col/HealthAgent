# Phase 7–10 计划：多 Agent、可靠性、UI 和观测

- 对应源码：`docs/phase-7-10-plan.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-7-10-plan.md](../../docs/phase-7-10-plan.md)

原文承接已有 Phase 0–6，按用户扩展范围规划到 Phase 10，并将提前开始的 UI 工作纳入 Phase 9；明确 Phase 11/12 不在该次范围。

四组目标相互关联：Phase 7 实现独立只读专业图及共享可信预算；Phase 8 增加有限读取重试、写入未知结果、故障注入和保守守卫；Phase 9 构建同源 React 工作台与严谨 SSE 状态机；Phase 10 持久化脱敏 Trace，并说明缺失 token/不可见重试。

验收要求既包括数据库/框架行为，也包括合成浏览器契约、真实 Uvicorn/SQLite 页面 smoke 和桌面/手机检查。交付仍采用规范七段格式，fake 的工程验证不能转述为医疗质量评测。

本文件是推进与验收清单，实际完成、限制和执行结果分别见 [Phase 7](phase-7-delivery.md.md)、[Phase 8](phase-8-delivery.md.md)、[Phase 9](phase-9-delivery.md.md)、[Phase 10](phase-10-delivery.md.md) 及 [汇总 JSON](phase-7-10-validation.json.md)。
