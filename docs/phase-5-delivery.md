# Phase 5 — RAG

## Completed

完成 TXT / Markdown / 文本 PDF 摄取、递归切分、embedding、SQLite 持久向量库、LangChain Retriever、search_health_knowledge 工具及证据引用元数据。普通上传为私人资料；公共知识由管理员本地命令导入。

## Files Changed

新增 `app/rag/`、`persistence/knowledge_repository.py`、DocumentIndex / KnowledgeChunk、`services/knowledge.py`、`tools/knowledge.py`、`api/documents.py`、`scripts/ingest_public.py` 和 RAG 集成测试；更新配置、lifespan、prompt 与依赖锁。

## Design

RecursiveCharacterTextSplitter 按中文标点、段落切分，每块最多 600 字符，目标重叠 80 字符，保留页码与页内偏移。默认 LocalHashEmbeddings 将词 / 汉字 n-gram 映射为固定 1024 维向量；这是确定性词面检索基线，不是神经语义 embedding。可显式配置 OpenAIEmbeddings 兼容服务；两种方式都走相同持久存储与 Retriever。

向量使用 SQLite JSON 列存储；SQL 先选择公共或当前用户私人文档，再在限定候选中计算余弦相似度，返回前再次核对 owner。片段含稳定 citation_id、文档 ID、文件、页码、偏移、来源及索引版本。不同用户或不同索引版本不共享去重标识。失败状态可查询；解析 / embedding 失败不发布部分索引，重复上传可重试。

## DeerFlow Reference

阅读 `community/ragflow/tools.py`、`community/ragflow/sources.py`、`agents/middlewares/knowledge_scope_middleware.py`，借鉴服务端范围限制与工具 evidence 格式。第一版不依赖 RAGFlow 远端服务，不复刻其 dataset 分组或复杂 Gateway scope 协议。框架接口核对 [递归切分](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)、[embedding 集成](https://docs.langchain.com/oss/python/integrations/embeddings/openai) 与 [pypdf 文本提取](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)。

## Tests

2026-10-03：初轮完整测试 **86 passed / 1 skipped**，18.10 秒。验证实际 Agent → RAG Tool → citation、重启检索、去重、公共 / 私人预过滤和普通用户不能发布公共资料。追加测试验证生成的文本 PDF 经 multipart 上传可检索、空白 PDF 明确失败、embedding 失败原子隔离及同文档重试；与实际 SDK 协议测试一起运行 **11 passed**，10.34 秒。最终全量结果见 Phase 6 验收记录。

## Known Issues

无 OCR；扫描、空白、加密 PDF 不支持。接受文档上限 2 MiB / 50 页 / 20 万字符 / 500 块；检索范围最多 5000 块，超过后明确失败。当前是小规模精确向量排序，无 ANN 索引。原始上传文件不额外落盘，只保留提取片段，重建 embedding 需用户重新提供原文件。神经语义 embedding 与真实 provider 尚未在线验证，医疗资料质量也未评测。公共知识不预填未经核验的医学内容。

## Next Phase

Phase 6：明确偏好提取、持久化、相关检索与上下文注入，区分 Memory 和 Health DB。
