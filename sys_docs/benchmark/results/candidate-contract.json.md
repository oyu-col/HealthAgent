- 对应源码：`benchmark/results/candidate-contract.json`
- 核对日期：2026-10-11
- 阅读源码：[candidate-contract.json](../../../benchmark/results/candidate-contract.json)
- 所属目录：[目录说明](README.md)

# 业务改进后的同协议复测：52/58

## 结构和执行条件

本文件仍采用manifest、summary、results结构。创建于2026-10-11 04:24:28 UTC，即北京时间12:24:28。与baseline同为contract、同29例、同2次重复、同seed及Python/依赖/预算；completed=true，case/grader/protocol/settings指纹保持相同，app_digest变为优化后业务源码指纹。

## 实际改善与保留失败

任务成功52/58，89.66%；相较基线增加2个通过样本。唯一由失败转通过的案例是rag_hash_collision_no_overlap，两次重复均改善。retrieval_hit与grounded_answer从10/14变为12/14，85.71%。

仍失败6行，来自三类案例各两次：

- rag_weak_word_overlap：界面“绿色”与蔬菜问题词重合仍导致不相关证据返回。
- timeout_read_bounded：tool.traced.query_exercise_records失败，且Trace不完整导致trace.terminal_execution失败。
- recovery_write_unknown：tool.traced.add_exercise_record及trace.terminal_execution失败；DB单条写入和随后查询检查仍满足。

不能把请求termination=completed解释为所有业务或审计检查通过。报告保留这些失败，没有伪造取消/超时后的工具结束回调。

## 观测完整性对指标的影响

tool_terminal_coverage仍为64/68，tool_execution仍54/64，recovery仍2/4。candidate将4份缺少真实工具结束事件的Trace标不完整，所以tool_calls、agent_steps分布的n从基线58变54；但task_success仍以全部58行计分。

均值差异不能脱离样本数阅读。案例墙钟均值约287.595ms、Trace执行均值约45.378ms，都是这次短运行的观察值；未控制缓存与机器负载，不将其单独当作已验证性能提升。

## 不能推出的结论

contract仍由脚本固定决策，工具选择与参数质量为N/A；没有模型token usage。哈希碰撞修复不能代表通用语义检索、模型规划或医学正确性提高。完整配对和无通过转失败结论以[comparison](comparison-contract.json.md)为准。

