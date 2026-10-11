- 对应源码：`benchmark/results/comparison-contract.json`
- 核对日期：2026-10-11
- 阅读源码：[comparison-contract.json](../../../benchmark/results/comparison-contract.json)
- 所属目录：[目录说明](README.md)

# 成对比较：2个改善、无通过转失败、6个保留失败

## 文件结构

比较产物不重复存储每条Trace，顶层包含comparable、mode、baseline_app_digest、candidate_app_digest、improved、regressed、unchanged_failures、baseline摘要、candidate摘要和interpretation。每个配对项是[case_id, repeat]，不能只按案例名合并两次运行。

## 实际配对结论

comparable=true、mode=contract。improved有2项：rag_hash_collision_no_overlap的repeat1和repeat2。regressed为空；unchanged_failures有6项，对应rag_weak_word_overlap、timeout_read_bounded、recovery_write_unknown各两次。

baseline任务成功50/58，candidate为52/58：从86.21%到89.66%，差值3.45个百分点。这里的“无回归”仅表示这58个配对中没有passed=true变false，不是对全部生产行为作无回归保证，也不表示仍失败项完全相同。

## comparable为什么成立

此值由[report.compare](../report.py.md)在校验完整报告后生成：案例、grader、运行协议、设置、模式、seed、选择集、重复数、Python和依赖相同；样本无重复、遗漏或额外项。业务app指纹允许不同，并单独记录为优化变量。

本文件使用两份输入摘要展示指标，不是数字签名；若需要审阅原始检查与Trace，应返回[baseline](baseline-contract.json.md)和[candidate](candidate-contract.json.md)。不得修改指纹绕过校验。

## 解释范围

提升是合成离线工程契约改善。provider-connection因模式、配置、选择集、重复数和grader不同，不在比较里。修正oracle前的旧试跑也不参与比较。

没有进行统计显著性检验；单个工程问题在两次重复中修复，不等于模型能力提升。工具/步骤的完整样本数发生变化，延迟也受运行环境影响，因此不把均值降低直接称为优化收益。

