# 已审阅的 Phase 11–12 评测结果

核对日期：2026-10-11。这里保留4份实际生成、经审阅的JSON结果；保留失败，不覆盖成“全通过”。它们不是测试夹具或模型标准答案。

## 文件与可确认结论

| 文件 | 角色 | 实际结果 |
| --- | --- | --- |
| [baseline-contract.json](baseline-contract.json) | 冻结案例、判分器和协议后的离线基线 | 29例×2次，50/58通过，86.21%。 |
| [candidate-contract.json](candidate-contract.json) | 业务代码优化后，同协议离线复测 | 同58个样本，52/58通过，89.66%。 |
| [comparison-contract.json](comparison-contract.json) | 严格按case_id、repeat配对的比较 | comparable=true；2个样本改善、0个样本由通过退回失败、6个样本仍失败。 |
| [provider-connection.json](provider-connection.json) | 一次真实provider连接尝试 | 只执行query_owner_weight一次；provider_unavailable，0/1任务通过，模型质量指标N/A。 |

50/58到52/58的提升为**3.45个百分点**，改善来自rag_hash_collision_no_overlap在两次重复中由失败变通过。其余通过/失败状态没有改变。这个结果证明本轮合成工程契约中的哈希碰撞误召回被修复，不能表示模型自然语言规划或医学回答质量提高。

## 为什么这两份contract报告可比较

两个报告都完整结束，模式contract、seed=20261011、repeats=2、29个所选案例、case/grader/protocol/settings指纹、Python与依赖版本相同；每个(case_id, repeat)恰好出现一次。业务app_digest不同，正是本轮优化变量。比较由[report.py](../report.py)执行，未修改JSON里的指纹绕过检查。

检索/固定事实代理指标retrieval_hit与grounded_answer均从10/14提高为12/14；该分母包含所有适用引用约束的任务，不只category=rag。contract的tool_selection、tool_arguments均为N/A，token_usage未知；不得补成零成本或100%模型准确率。

## 仍然存在的三类案例失败

| 案例 | 两次重复均失败的原因 | 不能据此声称什么 |
| --- | --- | --- |
| rag_weak_word_overlap | “绿色”界面说明仍被检索为绿色蔬菜问题的证据，触发禁止文档/最大引用数等约束。 | 无共享原词的哈希碰撞修复不等于解决词法重合造成的语义误召回。 |
| timeout_read_bounded | 读取超时已形成工具失败结果，但没有对应真实tool.finished终态事件；candidate还如实标记Trace捕获不完整。 | 请求完成或ToolResult正确不等于完整可审计的执行链。 |
| recovery_write_unknown | 写入未知后查询与最终单条数据库状态满足检查，但写工具的真实结束Trace缺失；candidate不再把该捕获标完整。 | 不能补造成功/失败回调把恢复案例强行判通过。 |

因此candidate仍有6/58失败。tool_terminal_coverage两轮都为64/68，故障恢复指标为2/4；这些不足保留在报告中。candidate的完整工具/步骤样本数从58变54，是对4条缺失结束事件的Trace作更诚实的完整性标记，不是少执行了4例。58个案例样本仍全部进入任务成功率分母。

案例墙钟延迟和Trace执行延迟均保留原始统计，但两轮短实验没有控制缓存、机器负载等因素；不将均值降低单独宣称为性能收益。

## provider连接报告不能加入前后比较

provider-connection.json记录一次真实模型请求未取得成功响应，错误链为连接异常，工具调用数为0。任务失败必须保留；质量指标分母为0，因为尚无模型决策可评估。其他“缺参数/缺工具/缺答案”失败检查是连接中断的后果，不能据此判定模型推理能力差。

这份报告使用较早的grader指纹，且模式、配置、选择集、重复次数与contract两轮不同。它只说明当时连接尝试失败，**不属于前后优化比较，也不是22个provider适用案例的完整评测**。连接问题解决后需使用当前冻结协议另建真实provider基线，再进行同模式复测。

## 试跑与归档边界

runs目录下baseline-contract-v1、baseline-contract-v2等属于修正数值/引用oracle前的探索性试跑，不能与本目录正式baseline/candidate比较。发现oracle会把随机UUID里的数字误当健康值后，已经先修正规则，再重跑冻结基线；没有对旧报告原地重评分伪造提升。

results中的JSON保持原样；后续实验另建输出，不覆盖本组证据。本目录README解释结果语义，不参与运行协议指纹。完整阶段交付和后续限制见项目docs中的Phase 11、Phase 12记录。

