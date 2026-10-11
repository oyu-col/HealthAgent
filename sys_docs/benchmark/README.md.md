- 对应源码：`benchmark/README.md`
- 核对日期：2026-10-11
- 阅读源码：[README.md](../../benchmark/README.md)
- 所属目录：[目录说明](README.md)

# Benchmark 使用说明文件

## 文件定位

原README面向需要真正运行评测的人，组织模式、命令、案例结构、指标解释、实验比较和数据边界。本页解释该README在项目中的作用；所在目录的README.md则是sys_docs自己的模块导航，二者通过保留原扩展名区分。

## 主要内容与代码依据

1. 两种模式：contract29例，provider22例；排除项在manifest.profile_excluded_cases中显式记录。
2. 从backend目录运行runner.py，使用现有虚拟环境。provider必须同时指定--mode provider和--allow-provider。
3. --cases、可重复--case-id、1到3次--repeats、--seed以及新输出目录约束，对应runner.main与run_suite。
4. 指标表解释task_success、工具约束覆盖、逐proposal参数准确率、终态工具尝试成功率、故障恢复、循环、延迟与真实usage。
5. compare要求同案例、grader、协议、预算、模式和运行环境，按case_id与repeat逐对比较。
6. 合成数据与内存observation、持久脱敏Trace之间的区别，避免把实际健康数据或凭据写入实验产物。

## 阅读中的关键限制

文件中的预算是评测BASE_SETTINGS及少数案例覆盖值，不应照搬为生产默认配置。temperature=0、固定随机seed不保证远端provider确定性；latency_ms包含建库和种子准备，agent_latency_ms才来自执行Trace。

README中的命令是复现方法，不是本页执行记录。具体通过数、失败案例和优化幅度应以不可覆盖的运行结果及阶段验收文件判断。模型服务连接失败应保留为任务失败，同时避免把未发生的模型响应计作质量得分。

## 维护位置

修改CLI时同步[runner说明](runner.py.md)，修改统计分母或比较条件时同步[report说明](report.py.md)，修改案例数量或profiles时同步[案例集说明](cases/health-v1.json.md)。此README不参与六个协议源码文件的protocol_digest，但其描述必须跟随实际代码。

