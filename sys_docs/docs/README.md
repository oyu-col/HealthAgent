# docs：架构决策、参考依据与历史验收

- 对应目录：`docs/`
- 核对日期：2026-10-11
- 实际目录：[docs](../../docs)

## 三类材料

**设计材料**解释为什么这样做：[architecture.md](architecture.md.md) 包含现状与最终目标；[phase-0-deerflow-analysis.md](phase-0-deerflow-analysis.md.md) 定位参考源码；[ui-deerflow-reference.md](ui-deerflow-reference.md.md) 记录 UI 借鉴与不采用的部分。计划文件说明推进顺序和验收要求，不自动证明执行结果。

**阶段交付**覆盖 Phase 0–12，每篇按 Completed、Files Changed、Design、DeerFlow Reference、Tests、Known Issues、Next Phase 七段组织。读到“尚无前端”等陈述时，应结合阶段日期：Phase 6 当时没有 UI，当前 Phase 9 已交付。这些文件是历史记录，不应为了说明当前状态直接改写过去结论。

**JSON 证据**包括参考源码哈希和各阶段实际验证摘要。参考快照记录被引用文件的内容版本，validation 记录当时运行命令/环境/通过/跳过/未执行范围。它们不是运行时配置，也不是每次启动自动更新的监控结果。

## 逐份导航

| 阶段或主题 | 文档说明 |
| --- | --- |
| 总体设计 | [architecture](architecture.md.md) |
| 参考分析 | [Phase 0 analysis](phase-0-deerflow-analysis.md.md)、[UI reference](ui-deerflow-reference.md.md) |
| Phase 0 | [交付](phase-0-delivery.md.md)、[静态验证](validation-results.json.md)、[参考快照](reference-snapshot.json.md) |
| Phase 1 | [计划](phase-1-plan.md.md)、[交付](phase-1-delivery.md.md)、[验证](phase-1-validation.json.md) |
| Phase 2–6 | [工具](phase-2-delivery.md.md)、[会话](phase-3-delivery.md.md)、[流](phase-4-delivery.md.md)、[RAG](phase-5-delivery.md.md)、[Memory](phase-6-delivery.md.md)、[验证](phase-2-6-validation.json.md) |
| Phase 7–10 | [计划](phase-7-10-plan.md.md)、[专业 Agent](phase-7-delivery.md.md)、[可靠性](phase-8-delivery.md.md)、[前端](phase-9-delivery.md.md)、[Trace](phase-10-delivery.md.md)、[验证](phase-7-10-validation.json.md) |
| Phase 11–12 | [计划](phase-11-12-plan.md.md)、[Benchmark](phase-11-delivery.md.md)、[优化与剩余失败](phase-12-delivery.md.md)、[验证](phase-11-12-validation.json.md)、[只读参考](phase-11-12-deerflow-reference.json.md) |

## 如何与代码配合

先在交付文档中找到某个设计动机和受影响文件，再到本套 sys_docs 相应镜像页阅读现有实现。目标目录不能当成真实文件清单，历史测试总数不能当作今天重新运行结果。Phase 11/12已有真实离线工程评测，在线模型连接仍受阻，任何工程pass都不能直接转成医学准确率。

原文档静态规则由 [verify_delivery.py](../backend/scripts/verify_delivery.py.md) 检查；本套镜像说明另有 [_meta 校验](../_meta/README.md)。2026-10-11更新随Phase 11/12实现进行，旧阶段验收保持历史值，新执行记录独立保存。
