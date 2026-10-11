- 对应源码：`benchmark/report.py`
- 核对日期：2026-10-11
- 阅读源码：[report.py](../../benchmark/report.py)
- 所属目录：[目录说明](README.md)

# 明确分母、失败保留和成对实验比较

## 核心函数

ratio返回passed、total和value；total为0时value为None。distribution返回样本数、均值、总体标准差、最小值和最大值；空样本统计为None。summarize聚合结果，markdown呈现人读报告，compare校验并比较两份完整实验。

## 各指标的来源与边界

| 指标 | 代码实际做法 |
| --- | --- |
| task_success | 全部执行行passed求和/结果行数；包括harness失败。 |
| tool_selection / tool_arguments / retrieval_hit / grounded_answer | 累加grader提供的passed/total，不自己生成语言判分。 |
| tool_execution | 从实际Trace的event=tool.finished读取布尔success；分母是已观测结束的尝试。 |
| tool_terminal_coverage | tool.finished数量/tool.started数量，显示终态观测覆盖。 |
| recovery | 仅recovery_eligible且fault_triggered>0的行；非异常的缓存重放不计入。 |
| loop | 全部结果中no_progress终态占比。 |
| unexpected_loop | 排除loop_detection案例后再算no_progress。 |
| tool_calls / agent_steps | 仅当该行所有Trace capture_complete且计数字段存在时，汇总成一个样本。 |
| latency_ms | 包括环境准备的每案例墙钟耗时。 |
| agent_latency_ms | 汇总具有latency_ms的持久Trace，含同案例重放产生的多个Trace。 |
| token_usage | 只加实际reported total；无已报告值为null。所有行有Trace且各usage.complete才算完整。 |

缺失或不完整Trace不当作零调用。known token总数可以是0，不能通过“0是假值”错误转成未知。失败类别由各行failure_categories累加；by_category仍保留失败样本在分类分母内。

## Markdown与隐私

markdown列出每个指标的实际分母/样本数，再逐case_id、repeat呈现通过状态、终态及失败检查名。没有把失败例隐藏到附录之外，也不输出原始回答、工具参数和健康正文。

token_usage完整结构保留在JSON中；Markdown当前循环主要输出比例与分布项。文字说明明确contract边界、代理groundedness、案例/Agent延迟差异，以及终态工具统计范围。

## compare为何严格拒绝差异

比较前两份manifest都必须completed。schema_version、Python、dependencies、mode、case/grader/protocol/settings指纹、selected_cases、repeats和seed必须存在且相同。关键指纹含app_digest都必须为非空字符串。

每份报告按selected_cases×1..repeats构造应有样本集合；重复case/repeat、漏例、多例、重复所选case、无效重复次数均拒绝。不能先转dict再静默覆盖重复样本。

通过校验后按(case_id, repeat)配对，生成improved、regressed、unchanged_failures，并带上两份摘要和业务源码app_digest。业务代码变化正是优化实验的目标，因此app_digest不要求相等；其他协议不能跟着改。

## 命令入口与限制

main读取baseline/candidate的JSON，调用compare，以排他创建模式写--output；已有比较文件拒绝覆盖。compare确认的是已提供报告的协议与样本一致性，不是防篡改签名、统计显著性检验或远端模型版本锁定。

同均值可能同时存在改善与回退；必须看配对列表。两次小样本的耗时变化不能单独证明性能优化。报告协议源码本身变更会改变protocol_digest，应重新建立基线。

## 验证

[test_benchmark_report.py](../backend/tests/unit/test_benchmark_report.py.md)覆盖真实event字段、空分母、harness失败保留、缺Trace未知usage、部分观测、故障恢复分母、预期循环分离，以及模式/指纹/运行环境不一致和重复/遗漏样本的拒绝。

