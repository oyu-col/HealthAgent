- 对应源码：`docs/phase-11-12-deerflow-reference.json`
- 核对日期：2026-10-11
- 阅读源码：[phase-11-12-deerflow-reference.json](../../docs/phase-11-12-deerflow-reference.json)
- 所属目录：[目录说明](README.md)

# Phase 11–12 的DeerFlow只读参考来源

## 数据结构与作用

该JSON记录reviewed_at、reference repository位置、reference_only、repository_modified、git_metadata_available及files数组。它为“参考了什么、采用什么、如何简化”提供可核验来源，不作为HealthAgent运行配置或依赖清单。

reviewed_at为2026-10-11，reference_only=true，repository_modified=false，git_metadata_available=false。因没有Git元数据，每条参考文件记录SHA-256，不能将其称作Git commit。

## 两份参考文件

| DeerFlow相对路径 | 采用思路 | HealthAgent中的适配 |
| --- | --- | --- |
| docs/experiments/task-continuity-20260912/task_eval.py | 独立核验任务产物/状态、预算约束、通过Trace定位失败。 | 改为实际健康SQL状态、SQL核验citation和现有LangGraph Runtime，不复制Agent循环。 |
| skills/public/skill-creator/scripts/aggregate_benchmark.py | 重复运行统计及前后差异呈现。 | 增加未知分母和严格案例/协议指纹比较，仅阅读参考脚本，没有调用该Skill。 |

path指向参考仓库内部位置；repository为相对HealthAgent项目的../deer-flow。SHA-256标识核对时文件内容，adopted说明借鉴的原则，adaptation说明没有照搬的业务边界。

## 如何使用与不能证明什么

阅读[Phase11交付](phase-11-delivery.md.md)或[Phase12交付](phase-12-delivery.md.md)中的DeerFlow Reference后，可以用本记录定位真实源码，并重新计算文件散列确认一致。

本文件中的repository_modified=false是此次只读参考的记录，不自动证明整仓每一文件都未被任何进程更改。项目另有参考快照和交付校验。源文件SHA相同也不代表参考实现已作为依赖安装、运行或通过HealthAgent测试。

出现skill-creator路径只是引用代码来源，不表示用户调用了技能，也不触发额外安装或审批。本项目评测执行器和grader仍由HealthAgent独立实现。

