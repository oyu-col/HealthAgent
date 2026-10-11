# knowledge.py：文档导入与检索服务

- 对应源码：`backend/app/services/knowledge.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/app/services/knowledge.py) · [目录说明](README.md)

## 职责和依赖

KnowledgeService 组合 [解析](../rag/parsing.py.md)、[embedding](../rag/embeddings.py.md)、[范围检索器](../rag/retriever.py.md) 与 [KnowledgeRepository](../persistence/knowledge_repository.py.md)。初始化固定当前 index_version，并创建进程内 _ingest_lock。上传接口、文本笔记接口和管理员公共导入脚本调用 ingest；Agent 的 search_health_knowledge 调用 search。

## ingest() 的输入与状态过程

输入为 user_id、filename、content(bytes)，可选 visibility=personal、source=user-upload。先检查合法文件名、非空且 ≤2 MiB、visibility 只能 personal/public、source ≤1000 字符；非法输入抛 invalid_document / HTTP 422。

在单个导入锁内：

1. 按文件 bytes 的 SHA256、owner、visibility、索引版本调用 Repository.begin，创建或复用元数据。
2. 若已经 indexed，直接返回同一文档，不重复解析或生成向量。
3. 在线程池运行 parse_and_split；异常保存 parse_status=failed、index_status=not_indexed、error_code=parse_failed。
4. 禁用该段自动 LangSmith tracing，并以 request_timeout_seconds 限制 aembed_documents；检查向量数量及各向量维度/有限值，标准化后组装 text、page、start_index、embedding。
5. embedding 阶段异常保存 parse_status=parsed、index_status=failed、error_code=embedding_failed；成功由 finish 一次发布所有片段和 indexed 状态。

解析/索引失败以可见元数据返回，并非 HTTP 请求必然报错；UI 必须读取 index_status，不能仅按 HTTP 200 显示“可检索”。原始文件 bytes 不在此处落盘，数据库保存的是文档元信息与解析文本片段。

## search() 的结果和失败分类

query 去空白后不得为空，长度 ≤2000；scope 为 personal/public/both，limit 为 1–10。非法参数返回 validation_error。服务构建每次查询独立的 ScopedVectorRetriever，以可信 user_id、当前 index_version 和维度约束候选；结果为 ToolResult，data 含 citations、embedding_mode、资料只能作为证据的 notice。

服务同时传入 `require_lexical_overlap=self.settings.embedding_mode == "local_hash"`。这是检索策略与配置模式的连接点：本地词法向量必须在查询和候选原文之间找到至少一个未散列的共同特征，防止哈希碰撞制造引用；provider 模式保留无共同字词的语义向量匹配。模型不能通过工具参数关闭该检查，普通 API 也没有暴露这一开关。

该策略不更改文档导入、向量计算、index_version 或现有库结构。它不解决所有弱主题重合问题，也没有把本地词法 embedding 改成语义模型。

查询同样受 request_timeout_seconds 限制且禁用自动外部 tracing。transient_failure 判断为瞬态错误时返回 retrieval_unavailable 且 retryable=true，使只读重试策略可识别；其他错误返回 retrieval_failed，不回显底层原始异常。

## 持久化与权限边界

pending 文档元数据和最终索引是两个事务；失败会保留状态，不发布半套向量。同内容失败后重新上传可复用文档并重试。_ingest_lock 只在本进程串行化导入，未提供后台队列、分布式锁或进度流。Service 内部允许 public；普通用户不能发布公共内容的权限约束由 HTTP API 不接收该参数实现，管理员脚本是独立入口。

[集成测试](../../tests/integration/test_rag.py.md) 覆盖 PDF/文本、失败后同 id 重试、出处、重启持久化和私人/公共隔离。[证据回归测试](../../tests/integration/test_retrieval_evidence.py.md) 通过真实 Service/Repository/SQLite 路径验证哈希碰撞被拒绝、正常证据仍返回且 owner/scope 不变；其中 provider 仅注入合成向量，不能作为在线 embedding 效果报告。扩展解析器或 embedding 时需同步 index_version，避免新旧索引混用。
