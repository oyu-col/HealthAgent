# test_retrieval_evidence.py：词法碰撞与检索证据边界回归

- 对应源码：`backend/tests/integration/test_retrieval_evidence.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/tests/integration/test_retrieval_evidence.py) · [测试目录](README.md)

## 作用与设计目的

Phase 12 的优化需要先确认真实失败，再以相同输入验证修复。本文件针对 local_hash 向量的哈希碰撞建立行为回归：检索得分高并不意味着原文包含查询依据，必须防止两个完全不同的词仅因散列桶相同而形成引用。同时保护正常召回、provider 模式和权限边界，避免修复一个负例却破坏其他路径。

它不使用预先写好的 ToolResult 来模拟检索。knowledge fixture 通过 database_session 创建临时真实 SQLite，组合 KnowledgeRepository、LocalHashEmbeddings 与 KnowledgeService；导入执行真实解析、分块、向量生成和索引发布，查询执行真实 SQL 范围过滤与 ScopedVectorRetriever。测试继承 conftest 的隔离配置和网络阻断，不读取本地 `.env`，不接触用户业务库。

## 各测试的输入与断言

### test_local_hash_collision_is_not_evidence

先确认默认 1024 维下 `synthetic3` 与 `synthetic68` 的向量完全相同，确保测试确实触发当前算法的碰撞。导入全文为 `synthetic3` 的 collision.txt，确认 indexed，再以 `synthetic68` 查询。期待服务成功返回，但 citations 为空。

这条断言不要求修改哈希算法，也不要求增加相似度阈值；它要求检索器独立确认词法证据。修复前实际返回了一条错误引用，因此测试曾真实失败。

### test_local_hash_keeps_actual_lexical_evidence

参数化的三个正例分别覆盖：

- 文档 `synthetic3` 对查询 `ＳＹＮＴＨＥＴＩＣ３`，验证全角字符和大小写经过 NFKC/lower 后仍能匹配。
- 文档 `daily walking diary` 对查询 `walking`，验证部分共享英文词项仍可返回证据。
- 合成中文睡眠计划对查询“睡眠计划”，验证中文单字/bigram 特征正常召回。

每个正例要求恰好一条引用，document_id 指向实际导入文档，text 与片段原文一致，citation_id 以 C- 开头且 page=1。该测试防止把过滤写成“整句完全相等”或针对样本字符串的特殊处理。

### SyntheticSemanticEmbeddings 与 test_provider_vectors_can_match_without_lexical_overlap

SyntheticSemanticEmbeddings 是离线受控向量夹具：所有输入返回相同单位向量。测试使用 embedding_mode=provider 的独立 Settings，但将此夹具直接注入 KnowledgeService；不会调用 embedding_session 或在线 SDK。配置中的 `.invalid` 地址及凭据字符串仅为测试值。

导入中文“入夜后安静休息。”，使用英文 `nighttime rest` 查询。两者没有本地词法共同项，但向量夹具明确给出匹配关系，因此必须保留该文档引用。该测试只证明 local_hash 的门控没有误作用于 provider，不证明真实跨语言语义质量或服务连接可用。

### test_lexical_evidence_keeps_owner_and_scope_filters

分别导入 Alice 私人文档、Bob 私人文档和 system-public 的公共文档，它们都包含 walking diary。以 Alice 身份查询 personal、public、both：结果集合必须分别等于 Alice 文档、公共文档、两者并集，任何范围都不能包含 Bob 的文档。

该断言保护新过滤不会绕过既有授权范围，也不会把 public 的 owner 不同误认为禁止访问。SQL 前置过滤的实现位置仍需结合 [KnowledgeRepository](../../app/persistence/knowledge_repository.py.md) 阅读。

## 与实现的关系

- [lexical_features](../../app/rag/embeddings.py.md) 让索引和过滤共享规范化/词法特征规则。
- [ScopedVectorRetriever](../../app/rag/retriever.py.md) 在 local_hash 路径拒绝零共同特征片段，并保留原阈值、排序与证据字段。
- [KnowledgeService](../../app/services/knowledge.py.md) 根据 embedding_mode 显式选择是否启用门控。
- [原有 RAG 集成测试](test_rag.py.md) 继续覆盖 PDF、失败索引重试、去重、重启持久化与 HTTP 发布权限。

## 实际验证与限制

2026-10-11 修复前执行本文件：1 failed、5 passed，唯一失败为碰撞错误引用。修复后将本文件与 test_rag.py 一起运行：11 passed，5.14 秒；相关四个 Python 文件的 Ruff 检查和格式检查通过。

并发运行 pytest 时，项目默认的 `.pytest-tmp` 会被其他测试进程占用；本次最终命令显式使用独立 `--basetemp=.pytest-tmp-rag-evidence`。此前共享临时目录的一次运行因 Windows SQLite 文件锁产生 fixture setup errors，没有把它解释成业务断言失败，也未删除其他进程占用的数据。

测试未证明所有不相关资料都会被拒绝。不同主题可能含共同字词，例如“绿色按钮”与“绿色蔬菜”；这种弱主题重合仍是 local_hash 的已知限制。该回归也不是在线模型、医疗准确性或性能基准。
