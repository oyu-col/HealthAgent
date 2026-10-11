# Phase 0 交付记录

日期：2026-10-03。阶段：DeerFlow Reference Analysis。

## Completed

- 新建独立 `HealthAgent` 目录，逐字节保留用户提供的规范。
- 完成 Lead、LangGraph / LangChain、Tool、Thread / State / Checkpoint、Streaming、Memory、SubAgent、Skill、FastAPI、Frontend 的源码定位与职责分析。
- 说明前端提交 → Gateway → Agent → Tool → stream → UI 的真实调用链。
- 核对当前框架官方文档，区分本地参考版本与线上 API，列出直接使用和应简化的能力。
- 完成最终目标目录、业务 / 权限 / 存储边界、阶段路线与 Phase 1 实施验收计划。
- 建立参考文件 SHA-256 清单，并执行文档静态校验。

## Files Changed

全部为 HealthAgent 内新增文件；没有修改 DeerFlow：

| 文件 | 内容 |
| --- | --- |
| [../README.md](../README.md) | 当前阶段、文档索引、项目边界 |
| [../AGENTS.md](../AGENTS.md) | 持续开发约定和阶段状态 |
| [../HEALTH_AGENT_SPEC.md](../HEALTH_AGENT_SPEC.md) | 原规范副本 |
| [../.gitignore](../.gitignore) | 密钥、构建产物与私有运行数据排除规则 |
| [phase-0-deerflow-analysis.md](phase-0-deerflow-analysis.md) | 源码定位、调用链、框架 API 与取舍 |
| [architecture.md](architecture.md) | 完整目标架构与目录 |
| [phase-1-plan.md](phase-1-plan.md) | 下一阶段文件、接口、顺序与验收 |
| [reference-snapshot.json](reference-snapshot.json) | 被引用参考文件的哈希、大小与行数 |
| [validation-results.json](validation-results.json) | 静态校验的实际输出 |
| 本文件 | 阶段交付与限制 |

## Design

Phase 0 只创建能指导后续开发的文档，不创建大量空业务目录。目标系统使用 create_agent 与官方 checkpointer / streaming，业务按 Tool → Service → Repository 分层，保持框架能力与健康领域逻辑的清晰边界。阶段计划明确单用户开发模式、用户隔离、数据持久化、重试幂等和真实评测的实施时机。

## DeerFlow Reference

详细真实路径与符号见 [源码索引](phase-0-deerflow-analysis.md)。核心借鉴：装配式 Lead、middleware 工具边界、thread 元数据与图状态分离、流事件转换、用户记忆注入、隔离委派、按需 Skill、FastAPI 生命周期和前端流消费。

缩减：不移植沙箱、动态插件、多 provider patch、Redis bridge、持久批任务、复杂 delta checkpoint 与完整 LangGraph Platform 兼容层。

## Tests

本阶段执行的是文档与源码引用检查，**不是单元测试或应用集成测试**。机器可读结果见 [validation-results.json](validation-results.json)：规范副本一致性、Markdown 本地链接存在性、参考文件快照一致性、核心符号行号、UTF-8 / 代码围栏 / 合并标记、Phase 0 文件范围、八项输出覆盖。

在线读取并核对了官方 Agents、Tools、Persistence、Streaming、Prebuilt middleware、Subagents 文档；引用放在 [框架能力表](phase-0-deerflow-analysis.md)。网页核对不等于本机 API 兼容性测试。

**未执行**：依赖安装、DeerFlow 启动、HealthAgent 单元 / 集成 / UI 测试、真实模型调用、Benchmark、性能测量。Phase 1 文档中的命令均为将来执行计划，没有标为通过。

## Known Issues

- 参考目录没有 Git 元数据，无法取得 commit、status 或 diff；文件哈希只能标记本次本地文件内容。
- 当前没有可运行应用；这符合规范第 32 节的首次任务范围。
- 尚未解算、安装和验证 HealthAgent 的依赖组合，也未验证真实 provider。不存在已确认的模型效果或评测提升。
- 本地源码引用依赖同级 `deer-flow` 目录；移动文档后需要同步相对路径。未来运行不会依赖该目录。
- RAG 向量库 / 中文 embedding 的具体选型留到 Phase 5 的本地样本验证，不把尚未比较的方案写成已验证结论。

## Next Phase

Phase 1 — HealthAgent Skeleton：按 [具体计划](phase-1-plan.md) 创建独立 Python / FastAPI / LangChain / LangGraph 最小工程，先以 fake 模型验证真实框架运行链路，再在具备配置时验证 provider。按规范本轮在 Phase 0 完成后停止，未提前进入 Phase 1。
