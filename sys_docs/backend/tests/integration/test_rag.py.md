# test_rag.py：文档索引、引用与授权检索

- 对应源码：`backend/tests/integration/test_rag.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/tests/integration/test_rag.py) · [测试目录](README.md)

## 范围与测试技术

使用临时真实 SQLite、local_hash embedding、真实解析器和 LangGraph 工具调用；PDF 在内存中用 pypdf 生成，所有内容为合成数据。httpx.ASGITransport 调用应用接口，不依赖外部网页、模型或 embedding 服务。

## 覆盖场景

1. **test_text_pdf_upload_and_scanned_pdf_failure**：构造含 Helvetica 文本流的单页 PDF，经 multipart 上传后 index_status=indexed；检索 walking diary 返回 page=1 且片段含 Synthetic walking。再导入无文本的空白页 PDF，parse_status=failed。虽然名称提及 scanned，实际 fixture 是空白无文字 PDF，不是扫描图像/OCR 样本。
2. **test_embedding_failure_is_atomic_and_retryable_by_upload**：替换 embedding 为抛 RuntimeError("SECRET") 的对象；导入后 parsed/failed，元数据不泄露 SECRET。恢复正常 embedding 后查询无失败文档片段；再次上传同内容使用同 document id，并转 indexed。
3. **test_ingest_deduplicate_retrieve_cite_and_persist**：同一 Markdown 笔记两次上传得到同 id；ToolChatModel 实际调用搜索，结果成功且有 citations，evidence.document_id、filename 对应真实导入，citation_id/index_version 非空。关闭重建应用后仍能检索相同 document_id。
4. **test_public_personal_isolation_is_applied_before_ranking**：分别导入 Alice/Bob 私人含唯一标记的资料和 system-public 公共资料；两人搜索都看到公共内容和自己的标记，不能看到另一人的标记。普通文本上传接口额外传 visibility=public 返回 422，防止用户发布公共知识。
5. **test_failed_ingestion_is_visible_without_partial_index**：损坏 PDF 保留 failed/not_indexed/parse_failed，检索 citations 为空；HTTP 上传带 ../../ 路径或 .exe 扩展名返回 422。

## 断言对应的设计

- 同内容 id 去重与重传恢复：[KnowledgeRepository.begin/finish](../../app/persistence/knowledge_repository.py.md)。
- 解析失败、embedding 失败与元数据状态：[KnowledgeService](../../app/services/knowledge.py.md)。
- 页码/片段：[parsing.py](../../app/rag/parsing.py.md)。
- SQL 范围限制和来源字段：[Retriever](../../app/rag/retriever.py.md)。
- 模型获取真实证据：[knowledge 工具](../../app/tools/knowledge.py.md)。

测试查询结果确实验证隔离，但“先于排序”的实现顺序还需结合 Repository SQL 阅读，结果断言本身不单独证明内部运算顺序。

## 未覆盖范围与维护

本文件没有真实 provider 的语义质量、OCR、数千片段容量压力、各种 PDF 布局精度或医疗引用有效性 Benchmark。失败重试是重新上传同内容，不是断言后台自动重建索引。更改索引版本、状态发布事务、owner 条件或分块出处字段时，应维持现有数据库和证据断言。

本次说明依据当前测试源码，不代表重新执行后的测试报告。
