# Phase 12 — Evaluation & Optimization

日期：2026-10-11。本次完成同协议的离线 Baseline → Failure Analysis → Optimization → Benchmark Again。真实模型在线对比受服务连接阻塞，用户确认保留连接失败记录，不再重试。

## Completed

正式基线 `baseline-contract-v3` 与复跑 `candidate-contract-v3` 各运行29例两次，共58个样本。案例、评分器、协议、设置、依赖及样本集合完全一致，compare返回 `comparable=true`。业务源码SHA-256不同，修复发生在保存基线之后。

| 指标 | 基线 | 修复后 | 解释 |
| --- | --- | --- | --- |
| Task Success | 50/58，86.21% | 52/58，89.66% | +3.45个百分点；两个改进样本均来自哈希碰撞案例 |
| 检索约束通过率 | 10/14，71.43% | 12/14，85.71% | 含RAG、多Agent与安全检索场景；不是只有类别rag的5例 |
| Grounded answer规则代理 | 10/14，71.43% | 12/14，85.71% | contract回答来自真实ToolMessage，不能外推模型回答质量 |
| 工具执行可见成功率 | 54/64，84.38% | 54/64，84.38% | 注入失败仍在分母中 |
| 工具终态覆盖 | 64/68，94.12% | 64/68，94.12% | 未补造4次不可见结束事件 |
| 注入故障恢复 | 2/4 | 2/4 | 未解决的Trace缺口仍使任务失败 |
| 非预期循环 | 0/54 | 0/54 | 另有4/58刻意循环案例正确停止 |
| 调用/步骤统计样本数 | 58 | 54 | Trace修复后排除4次不完整样本，均值变化不能称减少调用 |
| 案例平均耗时 | 367.963 ms | 287.595 ms | 含建库和准备；两轮波动不能证明性能提升 |
| Trace平均执行耗时 | 63.850 ms | 45.378 ms | 仅记录实测，本轮未做性能优化结论 |

两轮分别为25/29 → 26/29；新增通过2个样本、回归0个样本、仍失败6个样本。完整检查、事件和指纹见 [基线](../benchmark/results/baseline-contract.json)、[复跑](../benchmark/results/candidate-contract.json)、[正式对比](../benchmark/results/comparison-contract.json)。

## Files Changed

- `backend/app/rag/embeddings.py`：抽取共享 `lexical_features`，不改变原向量计算。
- `backend/app/rag/retriever.py`：可选原始词法特征交集门控，零交集不作为本地词面证据。
- `backend/app/services/knowledge.py`：只在 `local_hash` 模式启用门控。
- `backend/app/observability/recorder.py`：摘要完整性检查模型/工具started与ended的实际run_id配对。
- `backend/app/api/schemas.py`：healthz阶段标记更新为12；对应API测试、smoke与前端测试夹具同步。
- 新增 `test_retrieval_evidence.py`，扩充 `test_trace_recorder.py` / `test_observability.py`；阶段报告和sys_docs同步。

## Design

### 失败分析与修复一：哈希碰撞不是来源证据

基线案例 `rag_hash_collision_no_overlap` 使用无共同词项的 `synthetic3` 与 `synthetic68`；既有1024维哈希映射产生相同向量，余弦分数为1。单纯提高分数阈值不能排除该误召回。

先新增真实SQLite入库/索引/检索测试，旧实现1失败5通过；再抽出与向量算法完全相同的NFKC、lower、词/二元特征函数。仅local_hash要求query与chunk至少共享一个原始特征；SQL用户过滤、相似度阈值、排序不改，语义provider允许无相同词项的相关内容。向量和index_version兼容原索引，无需重建。修复后碰撞测试通过，中英文/全角词、用户隔离及模拟语义provider控制用例继续通过。

### 失败分析与修复二：缺少回调不可声明Trace完整

工具 `asyncio.timeout` 通过 `CancelledError` 取消执行；当前框架工具回调未对该路径发出finished。外层仍产生标准tool_timeout或write_outcome_unknown，DB核对正确，但Trace只有started。旧summary仅以终态和无事件丢弃判断完整，形成假完整声明。

先写8失败1通过的最小与真实LangGraph回归，再修改summary：终态、无丢弃且模型与工具的开始/结束run_id集合都相等，才capture_complete。并发同名工具按实际run_id配对，零调用缓存回放合法完整。没有根据工具名称或推测结果补造finished。因此相关两类benchmark仍失败，修复收益是准确暴露缺口，而不是人为增加通过数。

### 协议冻结与评分器校准

正式v3之前的试跑发现两项判分器问题：`SYNTHETIC-B4`被误抓成引用 `C-B4`，以及随机UUID含99触发另一用户数值禁止条件。分别添加ASCII引用边界与完整数值token/Decimal等值比较，新增测试后重新建立基线。旧v1/v2报告保留在runs，但因评分协议不同不参与增益对比。不得把判分器修正前后的分数当作业务优化。

## DeerFlow Reference

参考当前DeerFlow的任务状态独立核验、失败分类、重复统计和差异输出；采用范围与SHA-256见 [参考记录](phase-11-12-deerflow-reference.json)。本次UI没有新增工作流，仍沿用既有借鉴DeerFlow的侧栏/对话/资料面板布局，仅同步测试中的phase值。

## Tests

- RAG新旧回归11项通过；Trace新旧23项通过。
- 全后端352 passed、1 skipped（43.71秒）；Ruff及格式检查98文件通过。
- API smoke通过healthz、OpenAPI、chat、thread、memory、document index、TCP SSE、持久Trace及自身进程优雅关闭。
- 正式前后评测各58样本实际执行，compare通过且0回归；exit=1表示保留失败案例，非runner崩溃。
- 首次并行RAG测试与其他pytest共用临时目录出现文件锁；改用各自 `--basetemp` 后通过，全量验收用独立目录。初次Ruff错误地覆盖默认排除规则扫描了依赖目录；最终限定手写目录并使用extend-exclude，未改依赖。
- 前端和文档覆盖的最终实测以 [验收JSON](phase-11-12-validation.json) 为准；历史验收没有重写。

## Known Issues

| 保留的失败 | 实际含义 | 后续方向 |
| --- | --- | --- |
| `rag_weak_word_overlap` ×2 | “绿色”等少量词面重合仍可使无关主题文档召回 | 独立扩展负样本集、语义检索/重排，再保存新版本基线；不为单例调阈值 |
| `timeout_read_bounded` ×2 | 超时结果正确，但缺真实工具结束事件 | 引入服务端attempt关联的取消领域钩子，先验证并发与重试去重 |
| `recovery_write_unknown` ×2 | 实际写一次且查询确认正确，但被取消写工具缺结束事件 | 与上述相同；禁止重放不确定写入 |

真实provider在用户确认恢复后重试仍 `provider_unavailable`，诊断到 `SSLEOFError`；没有收到模型回答。用户确认当前不能修复网络/服务，保留记录。没有完整22例真实模型基线与候选对比，没有在线embedding结果，不宣称医学质量或真实模型成功率提高。

## Next Phase

规范Phase 12的本次离线工程闭环结束。下一轮先恢复真实模型服务，在当前代码上保存22例真实基线，再根据实际失败推进语义检索与完整取消Trace；扩展任务前必须版本化数据集和判分器。现有baseline-source本机副本仅用于溯源，不应覆盖当前代码。
