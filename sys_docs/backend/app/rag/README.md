# rag：解析、向量表示与有权限的检索

- 对应目录：`backend/app/rag/`
- 核对日期：2026-10-11
- 源码：[目录](../../../../backend/app/rag/)；上级：[app 说明](../README.md)

## 功能与设计目的

RAG 为 Agent 提供可追溯资料片段，减少仅靠模型记忆回答的需要。当前不自动生成权威医学知识，也不保证模型一定正确引用；返回的文档内容始终是待核对的数据。

- [parsing.py](parsing.py.md)：TXT/MD/PDF 校验、提取文本、保留页码并分块。
- [embeddings.py](embeddings.py.md)：确定性 local_hash 或显式配置的 provider embedding，以及共用词法特征提取、向量校验和索引版本。
- [retriever.py](retriever.py.md)：LangChain BaseRetriever，先取得已授权 SQL 候选，本地模式再检查实际词法交集，最后做余弦排序和出处包装。
- [__init__.py](__init__.py.md)：包说明。

## 两条流程

导入：HTTP 上传/文本笔记/管理员脚本 → KnowledgeService.ingest → parse_and_split → embedding.aembed_documents → KnowledgeRepository.finish。查询：search_health_knowledge → KnowledgeService.search → ScopedVectorRetriever → SQL owner/visibility/version 过滤 → query embedding → 本地模式校验未散列特征交集 → 排序 → 带 citation_id 的片段。

持久化与事务由 [KnowledgeRepository](../persistence/knowledge_repository.py.md) 处理；总超时、错误状态由 [KnowledgeService](../services/knowledge.py.md) 处理。RAG 内部不接受模型自行指定另一个用户身份。

## 实际边界

默认 local_hash 是词面 n-gram 向量，不是神经语义 embedding；PDF 只提取已有文本，没有 OCR。最多 2 MiB、50 页、20 万字符、500 片段；单次检索最多 5000 个已授权候选。未使用独立向量数据库、ANN、混合检索/reranker、网页抓取或后台索引服务。

Phase 12 排除了纯哈希碰撞的错误引用：当查询与片段没有实际共同特征时，本地向量即使得分很高也不能返回。该措施保留原向量和索引格式；无法解决“有少量相同字词但主题不同”的全部误召回，不能据此宣称医学或语义准确率提升。provider 模式不施加词法交集要求。

provider 模式会把查询/文档片段发往配置服务；不能把它写成纯本地处理。切换向量模型/维度/分块策略应升级 index_version 并重新导入原文。[测试](../../tests/integration/test_rag.py.md) 是合成文档上的工程验证，不是医学检索质量 Benchmark。

[证据边界回归](../../tests/integration/test_retrieval_evidence.py.md) 使用真实 SQLite 和导入流程，保护碰撞拒绝、正常召回、provider 模式边界和授权范围；模拟 provider 测试不访问线上服务。
