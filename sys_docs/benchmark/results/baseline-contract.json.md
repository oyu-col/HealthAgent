- 对应源码：`benchmark/results/baseline-contract.json`
- 核对日期：2026-10-11
- 阅读源码：[baseline-contract.json](../../../benchmark/results/baseline-contract.json)
- 所属目录：[目录说明](README.md)

# 冻结协议后的离线基线：50/58

## 报告结构

JSON顶层为manifest、summary、results。manifest记录执行条件、源码/案例/判分器/协议指纹及completed；summary含metrics、failure_categories和by_category；results按case_id与repeat保存逐例检查、终态、实际Trace、计数和文档key。

这是实际运行快照，不是要让模型复制的标准答案。报告原文没有自然语言答案全文或工具参数，可通过案例ID回到版本化语料理解任务。

## 本轮执行事实

创建时间为2026-10-11 04:20:16 UTC，即北京时间12:20:16。模式contract，seed=20261011，29个案例重复2次，selected_cases共29项、profile_excluded_cases为空，completed=true。

Python3.12.10；依赖记录为LangChain1.4.3、LangGraph1.2.12、langchain-openai1.6.7、SQLAlchemy2.1.3。模型标识contract-script-v1，本地local_hash 1024维；这些是报告记录的执行环境，不是泛化版本推荐。

| 指标 | 实际数值 |
| --- | --- |
| task_success | 50/58，86.21%。 |
| retrieval_hit / grounded_answer | 均为10/14，71.43%；有限规则代理。 |
| tool_execution | 54/64，84.375%。 |
| tool_terminal_coverage | 64/68，94.12%。 |
| recovery | 2/4，50%。 |
| unexpected_loop | 0/54；故意循环另计。 |
| tool_selection / tool_arguments | 分母0，null；固定脚本决策不算模型质量。 |
| token_usage | reported_total=null、complete=false，不估算成本。 |

## 失败证据

四种案例各失败两次，共8行：rag_weak_word_overlap、rag_hash_collision_no_overlap、timeout_read_bounded、recovery_write_unknown。前两种发生真实误召回；后两种工具业务输出已有归一化结果，但缺少对应真实tool.finished事件，tool.traced检查失败。

failure_categories的RAG Retrieval Error、Safety Violation、Tool Runtime Error不是互斥桶；同一案例可属于多类，不能把类别计数简单相加等同失败总数。

## 基线作用与可比性

本报告的case、grader、protocol、settings指纹与candidate完全相同，app_digest不同。它已经在数值/引用token判分修正后重跑，不能用旧runs/v1、v2替代它。具体逐对结论见[comparison](comparison-contract.json.md)。

本基线将4条工具结束事件缺失的Trace仍标为capture_complete，因而工具/步骤分布样本为58；candidate更诚实地将这些Trace标不完整。这不改变基线JSON，也不通过补造事件使本轮全过。基线存在观测问题本身就是后续分析的证据。

