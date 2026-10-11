- 对应源码：`benchmark/results/README.md`
- 核对日期：2026-10-11
- 阅读源码：[README.md](../../../benchmark/results/README.md)
- 所属目录：[目录说明](README.md)

# 评测归档说明的作用与结论边界

## 文件定位

源README为同目录4份JSON建立解释入口，明确baseline/candidate/comparison是一组可比较的contract实验，provider-connection仅是独立连接诊断。它将原始机器数据转为可审阅的中文结论，并保留失败与不可推断事项。

## 主要解释内容

- 29例×2次共58样本，50/58到52/58；增加2个通过样本即3.45个百分点。
- 2个改善都来自rag_hash_collision_no_overlap，没有通过变失败的配对；并非整个领域已解决。
- rag_weak_word_overlap、timeout_read_bounded、recovery_write_unknown各保留两次失败。
- candidate完整工具/步骤统计样本54，全部任务仍为58；不能把观测完整性变化误读为少执行案例。
- provider连接请求未取得成功模型响应，质量N/A；旧grader与不同执行模式使其不能参与优化前后比较。
- 修正数值/引用oracle前的v1、v2探索性试跑被排除，正式基线重新生成。

## 维护与限制

README属于结果解释材料，不是runner协议的一部分，也不改变JSON判分。新实验要新增结果，不把本轮说明中的50/58、52/58静默改成其他数字以制造连续成功记录。

它不声称临床有效性、在线embedding质量、token成本或统计显著的延迟优化。详细字段及证据路径见同目录四份JSON说明。

