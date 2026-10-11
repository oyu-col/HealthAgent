# embeddings.py：本地词面向量与 provider 适配

- 对应源码：`backend/app/rag/embeddings.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/app/rag/embeddings.py) · [目录说明](README.md)

## lexical_features(text)

提取本地向量与检索证据校验共同使用的、尚未散列的词法特征。先执行 Unicode NFKC 标准化和小写转换，再用正则提取英文/数字连续串以及单个中文字符（U+3400–U+9FFF）；返回这些单项与相邻两项拼接的 bigram。返回列表保留重复项，供向量计算累加词频；检索器则把查询侧列表转换为集合，判断候选原文是否确实含有共同特征。

将这段逻辑集中在一个函数，目的是防止建索引和检索过滤使用不同的规范化或分词规则。它不是中文分词模型，也没有停用词、医学同义词或主题分类能力。

## LocalHashEmbeddings

实现 LangChain Embeddings 接口，默认 1024 维。embed_query(text) 的确定性过程为：

1. Unicode NFKC 标准化并转小写。
2. 正则提取英文/数字串或单个中文字符（U+3400–U+9FFF）。
3. 特征包含单项以及相邻两项拼接的 bigram。
4. 对特征计算 blake2b 8 字节摘要，取模落入向量桶并累加计数。
5. 按 L2 范数归一化，空特征返回零向量。

其中前三步统一由 lexical_features(text) 完成。embed_documents(texts) 对每篇调用同一过程。它不下载模型、不学习语义，同词/相邻字匹配是主要能力，哈希碰撞会带来近似性，不能称为深度语义搜索。异步方法使用 Embeddings 接口提供的路径，当前类实现的是同步核心。

Phase 12 的回归样本证实，默认 1024 维时 `synthetic3` 与 `synthetic68` 的向量完全相同，尽管原词没有交集。向量相似度不能单独证明存在词法依据；[检索器](retriever.py.md) 因此在 local_hash 模式检查未散列特征的交集。哈希函数及向量数值仍保持原算法，没有为某个样本更改桶映射。

## normalize_vector(vector,dimensions)

要求长度等于配置维度，元素属于 int/float 且有限；无效抛 ValueError。非零向量 L2 归一化，零向量保持全零。这里校验数值与长度，不验证向量来自何种模型；模型兼容性依靠 index_version 隔离。Python bool 是 int 子类，当前 isinstance 检查并未额外排除它，不应描述成严格仅普通数字类型。

## embedding_session(settings)

asynccontextmanager 统一资源生命周期：

- local_hash：yield LocalHashEmbeddings，无 HTTP 客户端。
- provider：持有同步/异步 httpx 客户端，超时取 model_timeout_seconds；构建 OpenAIEmbeddings，传模型、维度、配置密钥/base_url、客户端、max_retries、request_timeout；check_embedding_ctx_length=False，chunk_size=32。

退出上下文关闭客户端。provider 是 OpenAI 兼容 embedding SDK 适配，不保证任意聊天服务都支持相应模型或 dimensions 参数。密钥只从 settings 传入，本文不读取或记录实际值。文档原文片段与查询会送至配置服务，默认本地模式则不联网。

## index_version 与更新策略

版本字符串包含 embedding_mode、模型标识（本地为 lexical-ngram-v1）、维度，以及 chunk600-overlap80-v1。查询与候选 SQL 必须使用同一版本；更换模型/维度后旧向量仍可在库中存在，但不会混入当前版本查询，需要重新导入原文件。

本次抽取 lexical_features 和增加检索时的证据过滤，没有改变向量或分块格式，因此保留当前 index_version，已有索引可继续使用。若后续更改分词、ngram 构造、哈希算法或归一化方式，则不能沿用这一兼容性结论。

[KnowledgeService](../services/knowledge.py.md) 检查文档向量数量，逐向量调用 normalize_vector；[Retriever](retriever.py.md) 也验证查询和候选向量。[RAG 测试](../../tests/integration/test_rag.py.md) 使用本地向量与故障注入，不代表真实 provider 检索效果评估。[证据回归测试](../../tests/integration/test_retrieval_evidence.py.md) 同时保护碰撞拒绝、规范化后的真匹配和 provider 路径的语义匹配能力。
