# Phase 2–6 验证 JSON：工具到 Memory 的闭环

- 对应源码：`docs/phase-2-6-validation.json`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-2-6-validation.json](../../docs/phase-2-6-validation.json)

顶层 phases=[2,3,4,5,6]，记录时间为 2026-10-03。executed 下保存 locked_offline_install、pytest、Ruff、http_smoke、各阶段里程碑以及真实 SDK MockTransport 协议检查；static_checks 和未执行项说明独立性与验证范围。

最终 pytest 为 95 passed / 1 skipped，21.38 秒；67 个 Python 文件格式检查通过，uv 离线锁安装解算记录 71 packages。阶段 75/79/83/86/90→95 是不同时间的回归里程碑，不是可以相加的独立测试总量。

HTTP smoke 使用 fake 和临时数据，在 49384 端口验证会话、偏好、文档、TCP SSE，并记录 child_process_stopped、port_closed、temporary_database_cleaned。SDK 协议项明确 live_network=false、httpx.MockTransport，不应误称在线模型通过。

文中没有 Phase 7 专业 Agent 或 Phase 9 UI 的验收；后者查 [Phase 7–10 数据](phase-7-10-validation.json.md)。本记录适合判断基础存储/恢复/检索/偏好何时完成，具体设计见 [Phase 6 交付](phase-6-delivery.md.md)。
