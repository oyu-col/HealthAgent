# Phase 0 源码分析：参考依据与缩减决策

- 对应源码：`docs/phase-0-deerflow-analysis.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-0-deerflow-analysis.md](../../docs/phase-0-deerflow-analysis.md)

本文件记录对本地 DeerFlow 真实代码的阅读：范围与证据、源码索引、请求往返链路、各模块职责、可直接使用的框架能力和借鉴/不采用清单。它为独立实现提供理由，不将参考仓库变成 HealthAgent 的运行依赖。

模块分析覆盖 Lead/Runtime、Tool、Thread/Checkpoint、Streaming/FastAPI/Frontend、Memory、SubAgent、Skill、Reliability/Trace。源码符号和行号用于定位当时文件；[reference-snapshot.json](reference-snapshot.json.md) 保存内容身份，参考文件更新后行号可能失效。

取舍包括保留装配式 create_agent、公开 context、官方持久化与流接口、服务端权限和中间件边界；不照搬沙箱、多 provider patch、Redis bridge、完整 Gateway 兼容层与复杂后台任务系统。Skill 的参考分析不等于现有工程已经加载领域技能。

原文有当时核对过的官方框架资料，但那是阶段记录；当前兼容性要以项目锁定依赖及实际测试为准。本次只说明该文档用途，没有重新联网核实外部文档。

读完可顺接 [架构方案](architecture.md.md)、[Phase 1 计划](phase-1-plan.md.md) 与现有 [Runtime 说明](../backend/app/agent/runtime.py.md)。
