# Phase 11 — Domain Benchmark

日期：2026-10-11。工程实现完成，实际在线模型能力验收因连接故障未完成；用户确认本次保留失败记录。该限制不由 contract 模式替代。

## Completed

- 建立29个版本化合成案例，覆盖规范要求的12类任务；contract执行29个，provider执行适用的22个，排除项在manifest公开。
- 实现严格case schema、隔离环境、真实API执行器、独立SQL/工具/引用/Trace观察器、任务判分器、指标统计和同协议比较。
- 输出任务成功、工具选择、工具参数、工具执行、恢复、循环、调用/步骤、延迟、检索与groundedness代理指标，并公开分母、未知和观测覆盖率。
- 模型不获取期望状态或答案。查询验证实际返回行，写入验证真实数据库及幂等回放，RAG citation核对实际SQL片段和owner/visibility。修改oracle不能改变模型决策的集成测试已通过。
- 基线和修复后结果均实际运行并保存在 `benchmark/results/`，详细对比见Phase 12。

## Files Changed

| 文件 / 目录 | 职责 |
| --- | --- |
| `benchmark/cases/health-v1.json`、`schema.py` | 29个案例、严格校验及两种profile |
| `benchmark/runner.py`、`environment.py`、`model.py` | 临时应用/数据库、种子/故障注入、显式contract或provider执行 |
| `benchmark/observation.py`、`graders/task.py` | 实际SQL、ToolResult、工具提议、引用和Trace判分 |
| `benchmark/report.py`、`README.md`、`results/` | 指标、对比、运行说明和实际证据 |
| `backend/tests/unit/test_benchmark_cases.py`、`test_benchmark_graders.py`、`test_benchmark_report.py` | 输入边界、独立判分与样本/指纹比较保护 |
| `backend/tests/integration/test_benchmark_runner.py` | 真实查询、回放不重复写、实际citation及临时目录清理 |
| `README.md`、`AGENTS.md`、`docs/architecture.md`、`sys_docs/` | 使用入口、约定、架构和逐文件说明同步 |

## Design

执行采用现有 LangChain/LangGraph，Benchmark 不实现第二套 Agent 循环。每个案例创建自己的 app lifespan、SQL数据库和官方checkpointer；种子通过真实Service写入，业务请求走ASGI HTTP API。fault只patch当前临时app实例，结束恢复，不向生产工具暴露故障参数。

contract仅固定工具决策，实际工具/Service/DB/RAG仍运行。provider只读必要的模型配置，使用合成输入和有界预算；不加载原健康数据。默认model最多16次、tool最多12次共享预算，每次输出上限1200 tokens，SDK重试0，案例请求上限90秒。具体案例可使用schema约束的预算覆盖。重复1–3次，默认种子20261011；真实服务不保证种子确定性。

grader把模型声称、真实工具结果和最终数据库分开看待，响应“成功”不能替代状态核验。列表比较为不计顺序的等大小多重集合，防止额外用户行被部分匹配漏过。参数准确率逐真实proposal计分，先错后对仍保留前次错误。纯数值按完整数值token匹配，引用按ASCII token边界提取，避免随机UUID和文档编号产生误判。

Task Success要求所有检查通过。工具选择是必需/禁止约束覆盖率，不宣称调用precision；contract的选择/参数分母为0。工具执行只统计观测到finished的尝试，额外报告finished/started比例。调用均值只使用完整Trace并给出样本数；缺失usage为null。连接失败且无成功模型响应时保留任务失败，但质量分母为0。固定事实与citation规则是合成groundedness代理，不是临床质量评价。

manifest保存案例、grader、protocol、app、设置指纹及Python/依赖版本。compare拒绝未完成、缺失/重复样本、模式/参数/协议不一致的报告。病例内容、密钥、服务地址、原始异常和完整模型载荷不写报告。

## DeerFlow Reference

只读参考当前仓库的 `docs/experiments/task-continuity-20260912/task_eval.py`：任务成功需与产物/状态和预算约束核对；本项目改为健康SQL状态与真实citation，并复用原有Runtime。

只读参考 `skills/public/skill-creator/scripts/aggregate_benchmark.py`：重复运行统计和差异呈现；本项目增加N/A分母和严格可比性检查，没有调用该Skill或复制其执行器。路径、指纹与采用边界见 [参考记录](phase-11-12-deerflow-reference.json)。没有修改或依赖DeerFlow。

## Tests

- schema 23项、grader 128项、report 26项、runner集成5项通过；均计入全量后端回归。
- 全量离线后端：352 passed、1 skipped；skip为需要 `--run-live` 的旧连接测试，独立Benchmark实际连接探测另有记录。
- Ruff对手写后端和Benchmark的98个Python文件检查、格式检查通过。
- 真实provider共尝试3条单案例连接请求，均没有得到模型回答；最终探测为TLS连接关闭。最新脱敏报告见 [provider-connection.json](../benchmark/results/provider-connection.json)。不把这3次失败冒充完成22例在线评测。
- 正式离线基线/复跑、API烟雾及前端验证结果见 [机器可读验收](phase-11-12-validation.json)。

## Known Issues

在线服务当前不可达；因此工具自主选择、参数生成、语言理解及真实模型安全性没有完整实测结论。provider模式7个排除案例还需在未来扩展为稳定的在线故障协议。规则判分只覆盖预定义事实，不替代语义评审或临床验证。

工具取消可能缺少框架finished事件，当前报告明确暴露覆盖率。少量词语相同但主题无关的本地检索结果仍可能误召回。所有失败样本保留，没有为了分数删除。

本次前后评测在同一安装环境运行；manifest只记录四个核心包版本，未指纹覆盖完整依赖树，因此不能保证跨环境完全一致。compare以生成报告为可信输入，没有重算被手工篡改的summary；本次已交叉核对逐例与摘要一致。个别provider若为同一模型run补发结束回调，参数proposal可能重复计数，需在线扩展回归。上述属于未来协议增强点，未在冻结v3过程中临时改分母。

## Next Phase

Phase 12已经完成本次离线优化闭环。服务恢复后先在同版本业务代码留存真实模型基线，再进行下一轮优化和可比较复跑；不要把本次连接失败作为模型能力基线。
