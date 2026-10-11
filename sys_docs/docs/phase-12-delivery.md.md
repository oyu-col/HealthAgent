- 对应源码：`docs/phase-12-delivery.md`
- 核对日期：2026-10-11
- 阅读源码：[phase-12-delivery.md](../../docs/phase-12-delivery.md)
- 所属目录：[目录说明](README.md)

# Phase 12 的真实失败分析、业务修复和同协议复测

## 文件定位

源文件记录已经发生的一次离线Build→Benchmark→Trace→Failure Analysis→Optimization→Benchmark Again闭环。它将业务修复与评分器校准分开，并保留未解决案例。真实provider前后能力对比仍受连接问题阻塞，不能宣称已经取得线上质量提升。

## 正式实验结论

baseline-contract-v3与candidate-contract-v3均为29例各重复2次、58样本。case、grader、protocol、settings及Python/依赖相同，业务app指纹不同，compare确认可比。

任务成功50/58到52/58，即86.21%到89.66%，增加3.45个百分点。两次改善都来自rag_hash_collision_no_overlap；没有passed变false的配对，仍有6条失败。检索/groundedness规则代理10/14到12/14，分母包含RAG、委派与安全检索任务，不能只按category=rag数量理解。

工具终态覆盖仍64/68，故障恢复仍2/4。candidate完整调用/步骤样本从58变54，因为Trace开始诚实地标明4条缺结束事件；不能把均值降低解释为少调用或性能优化。两轮耗时只记录观察值，没有足够控制条件建立性能结论。

## 修复一：词法哈希碰撞

基线中synthetic3与synthetic68无共同原词，却映射为相同1024维向量、余弦为1，提高分数阈值也无法拒绝。修复先抽取既有NFKC、lower、词与二元特征逻辑为lexical_features，保证原向量算法和index_version不变。

KnowledgeService仅为local_hash启用query/chunk原始特征交集门控，零交集不返回证据；SQL权限过滤与排序仍保留。语义provider不适用该门控，以免误拒无字面相同但语义相关的结果。实际SQLite回归同时包含中英文、全角、用户隔离及模拟provider控制。

## 修复二：Trace不可宣称虚假完整

asyncio.timeout会取消工具；当前框架某些路径没有finished回调。业务边界仍产生tool_timeout或write_outcome_unknown，但旧summary只看“终态且无丢弃”就标完整。

修复要求模型与工具开始/结束run_id集合都一致。并发同名工具按run_id配对；合法零调用回放仍完整。实现没有根据工具名或推测结果补造结束事件。因此timeout_read_bounded和recovery_write_unknown继续失败，这体现严格证据要求，而不是修复未生效的矛盾。

## 评分器校准不计作业务提升

早期v1/v2试跑暴露SYNTHETIC-B4被误提取C-B4、UUID含99被误当禁止健康值的问题。引用ASCII边界与Decimal完整数值匹配修复后，重新冻结grader和协议并重跑v3基线；旧试跑不参加正式比较。

## 当前剩余问题

rag_weak_word_overlap的“绿色”词面重合依然误召回；两个超时/未知写入案例依然缺真实结束Trace，各重复2次，共6/58失败。未来需要独立扩大负例、语义检索/重排，以及可关联attempt的取消领域事件，不能专为单例调整阈值或自动重放不确定写入。

源文件还记录provider连接在重试后仍失败，诊断涉及SSLEOFError；没有完整22例在线基线/候选，也没有在线embedding验证。最新[连接报告说明](../benchmark/results/provider-connection.json.md)仅证明连接尝试结果，不用于推断模型能力。

## 验证与历史保留

文件列出RAG回归11项、Trace23项、全后端352通过1跳过、Ruff98文件及API smoke；前端/文档最终结果指向[验收JSON](phase-11-12-validation.json.md)。早期并行pytest临时目录锁和Ruff误扫依赖目录有如实记录，最终检查采用独立basetemp和手写目录范围。

此交付文件不改写旧阶段验收，不覆盖runs中的探索性输出，也不建议用baseline-source本机快照覆盖现代码。

