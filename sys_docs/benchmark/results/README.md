- 对应目录：`benchmark/results/`
- 核对日期：2026-10-11
- 实际目录：[results/](../../../benchmark/results/)

# 已审阅评测证据目录

## 目录职责

这里归档Phase 11–12实际执行形成、已核对含义的四份JSON。它与runs探索性输出不同：归档对象应明确哪一组可以正式比较、哪些只能用于失败诊断。报告保存原值，说明文件解释其结构和结论边界。

| 文件说明 | 阅读目的 |
| --- | --- |
| [README.md](README.md.md) | 解释总体结果、三类保留失败、provider限制与试跑排除。 |
| [baseline-contract.json](baseline-contract.json.md) | 50/58的冻结离线基线、实验配置及原始失败检查。 |
| [candidate-contract.json](candidate-contract.json.md) | 同协议52/58复测，以及Trace完整性标记的变化。 |
| [comparison-contract.json](comparison-contract.json.md) | 2个配对改善、无通过转失败和6个保留失败的严格比较。 |
| [provider-connection.json](provider-connection.json.md) | 单次真实连接失败，区分基础设施问题与模型质量。 |

## 可确认事实与限制

29个contract案例各重复2次，任务成功率从86.21%到89.66%，提升3.45个百分点。改善仅来自哈希碰撞工程回归的两次重复，未证实模型规划或医学质量提高。三类案例仍失败：弱词重合、超时终态Trace缺口、写入未知恢复的终态Trace缺口。

provider报告只有一个案例一次请求，且使用较早grader；它不属于两轮contract比较。旧runs/v1、v2试跑在oracle纠正前产生，不能拿来扩大提升幅度。

## 阅读与维护顺序

先读原README的结论边界，再看comparison配对列表，回到两份完整报告定位checks和Trace。理解统计代码可见[report.py说明](../report.py.md)。后续实验应另建产物，不原地修改JSON；本镜像页中的固定数字是2026-10-11这组已审阅证据的记录，不是未来所有版本的承诺。

