- 对应目录：`benchmark/`
- 核对日期：2026-10-11
- 实际目录：[benchmark/](../../benchmark/)

# Benchmark：独立、可复现的健康任务评测

## 目录定位与设计目的

本目录为 Phase 11 建立领域任务基准，为 Phase 12 提供“基线—失败分析—业务修改—同协议复测”的闭环。它位于后端 app 之外，生产请求不依赖评测包；运行时主动构造临时应用，复用项目真正的 Service、Repository、LangGraph、checkpoint、API 与 Trace。

当前案例集包含29个合成任务，覆盖规范要求的12类场景。contract运行29例；provider运行其中22例，余下7例用于可控故障、循环及哈希碰撞工程回归。两种模式均固定使用 local_hash 索引。数量是源码清单，不表示29例已经通过；实际结果应以阶段验收和对应实验报告为准。

## 文件与数据流

| 文件或子目录 | 职责 |
| --- | --- |
| [README.md](README.md.md) | 给使用者说明运行命令、指标分母、隐私和比较条件。 |
| [schema.py](schema.py.md) | 校验案例结构、模式、预算、证据引用和枚举。 |
| [cases/](cases/README.md) | 保存合成用户问题、种子环境及独立判分条件。 |
| [environment.py](environment.py.md) | 准备实际数据与文档；在单个应用上注入有限故障。 |
| [model.py](model.py.md) | contract专用脚本模型，只读execution_plan。 |
| [runner.py](runner.py.md) | 驱动整个应用生命周期、请求、判分和报告写入。 |
| [observation.py](observation.py.md) | 采集真实工具提议、ToolResult、SQL快照及校验证据。 |
| [graders/](graders/README.md) | 将真实状态与独立期望比较，输出检查项和失败类别。 |
| [report.py](report.py.md) | 汇总明确分母的指标，并严格比较成对实验。 |
| [results/](results/README.md) | 归档已审阅的真实基线、候选、配对比较与独立provider连接报告。 |
| [__init__.py](__init__.py.md) | 包说明，无启动副作用。 |

执行顺序为：load_cases → 选择profiles → 临时create_app → seed → 注入故障 → /api/chat（必要时replay/resume）→ 读取数据库/checkpoint/Trace → SQL核验证据 → grade_case → summarize。报告完成后才允许compare。

## 两种模式应如何理解

contract用预设动作控制模型选择，但工具、存储、检索与故障处理实际执行。它能证明某个决策序列经过系统后是否得到正确状态；不能证明模型能够自主产生该决策。其工具选择、参数质量分母为0。

provider将用户input交给真实配置模型，不把expected字段或execution_plan发送给模型。仍使用合成数据库和本地词法索引；它测得的是当前模型、当前业务代码、当前合成任务共同产生的表现，不是临床有效性。

## 输出与源码边界

本镜像说明 authored 源文件、配置案例和results中已审阅的阶段证据。runs属于临时实验输出，不生成逐文件镜像；[results说明](results/README.md)记录本轮50/58到52/58的离线工程改善及保留失败。不要把一次失败的输出目录覆盖为成功，也不要在改grader后沿用旧基线声称提升。

可从[后端Benchmark集成测试](../backend/tests/integration/test_benchmark_runner.py.md)理解真实执行，从[判分器测试](../backend/tests/unit/test_benchmark_graders.py.md)理解如何阻止回答自证成功。

