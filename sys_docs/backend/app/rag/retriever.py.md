# retriever.py：先授权再排序的向量检索器

- 对应源码：`backend/app/rag/retriever.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/app/rag/retriever.py) · [目录说明](README.md)

## 类型与输入

ScopedVectorRetriever 继承 LangChain BaseRetriever，持有 repository、embedding、可信 user_id、当前 version、dimensions；scope 默认 both、k 默认 5，require_lexical_overlap 默认 False。同步 _get_relevant_documents 直接抛 NotImplementedError，必须通过 ainvoke 使用异步实现。

require_lexical_overlap 由 KnowledgeService 根据 embedding_mode 显式设置：只有 local_hash 为 True。它是内部检索策略开关，不由模型工具参数决定。provider 的语义向量可能在没有共同字词时表达相关含义，因此不能一并应用该过滤。

user_id 由 KnowledgeService 创建检索器时注入，模型只能选择 scope，不能传另一个 owner。scope 和 k 的合法范围由 [Service](../services/knowledge.py.md) 校验。

## _aget_relevant_documents() 的流程

1. Repository.candidates(user_id,version,scope) 在 SQL 中限制私人 owner/公共域、版本和 indexed 状态。
2. 返回候选超过 5000 时抛容量错误；Repository 的 5001 上限用于发现超量，而不是截取前 5000 后继续给不完整答案。
3. aembed_query 生成查询向量，再 normalize_vector 验证维度及有限值。启用词法检查时，通过 lexical_features 一次生成查询的未散列特征集合。
4. 在线程池中的 rank 遍历候选。第二次检查 visibility/owner，防御 Repository 返回越界私人数据。
5. 当 require_lexical_overlap=True 时，对候选原文提取同一套词法特征；若与查询集合没有交集，跳过此片段，不让纯哈希桶碰撞成为引用。特征包括规范化后的英文/数字串、中文单字与相邻项 bigram，算法与本地建索引一致。
6. 对剩余候选向量归一化，计算点积（单位向量的余弦相似度），只保留 score≥0.08；按分数降序、chunk.id 次序排序，返回前 k 个。

检索采用全候选线性扫描，没有 ANN 索引或数据库内向量排序。归一化/排序放线程池减少阻塞事件循环，但候选仍需一次加载到应用内存。

## 输出的证据结构

每个返回 Document 的 page_content 是片段原文，metadata 含：

- citation_id=C-加 chunk UUID、document_id；
- filename、page、start_index、source、visibility；
- index_version、六位小数 score。

没有命中时返回 []，不是虚构引用；0.08 为当前工程筛选阈值，不是医疗可信度或概率。出处字符串不会被检索器访问，也不校验出版物真实性。

## Phase 12 修复的具体问题与限制

默认向量中，全文为 `synthetic3` 的片段与查询 `synthetic68` 的向量余弦为 1，但原始特征没有交集。过滤前它会被返回为证据；现在 local_hash 路径拒绝该片段。这不是提高相似度阈值，也不依赖样本字符串名单。

该检查只排除“没有共同特征却因为散列碰撞得分”的候选，不保证主题相关。例如描述“绿色按钮”的界面说明与“绿色蔬菜”的问题仍可能因共同文字通过，必须在评测中保留这一限制。它也不是医学真实性校验，不能把通过门控理解为结论可信。

向量与分块算法未变，检索直接使用库中片段文本校验，不新增数据列，也不要求重建索引。每个 local_hash 候选多一次词法提取；当前仍为最多 5000 个候选的线性扫描，没有宣称时延优化。

## 错误与维护

向量非法、容量超限、embedding 故障都交给 KnowledgeService 转成安全 ToolResult。异步取消正常向上传播。文档片段不能升级成系统指令，工具说明和上层 prompt 负责维持数据边界。

[集成测试](../../tests/integration/test_rag.py.md) 断言 Alice/Bob 私人片段不会互见、公共片段两人可见、引用信息可回溯且重启保留。[证据回归测试](../../tests/integration/test_retrieval_evidence.py.md) 额外覆盖实际哈希碰撞、英文规范化/共享词/中文真匹配，以及不含共同词项的模拟 provider 向量合法召回。扩展混合检索、阈值或 reranker 时，要保留“授权发生在排名前”的设计。
