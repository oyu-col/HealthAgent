- 对应源码：`backend/app/api/documents.py`
- 核对日期：2026-10-04
- 阅读源码：[documents.py](../../../../backend/app/api/documents.py)
- 所属目录：[目录说明](README.md)

# 私人健康文档上传与列表接口

## 定位与设计目的

路由前缀 /api/documents，对当前用户提供文本摄取、文件上传、文档列表。它处理 HTTP 输入和资源关闭，解析/分块/embedding/发布索引由 KnowledgeService 完成，不在路由里实现 RAG。

## 入口与流程

- POST /text：TextDocumentRequest 拒绝额外字段并去除字符串首尾空白；text 长度为 1 到 MAX_CHARS。filename 经 validate_filename 验证后还必须以 .txt/.md 结尾。将内容转 UTF-8 字节后调用 knowledge.ingest。
- POST /upload：从 UploadFile 最多读 MAX_BYTES+1 字节，超限立即抛 document_too_large/413；以可信 user_id、原文件名或空串、字节内容调用 ingest。finally 始终关闭上传文件。
- GET 根路径：直接调用 knowledge.repository.list(user_id)，用 documents 数组包装结果。它是已有状态列表，不重新解析文件。

## 返回与边界

摄取返回文档记录，其中 parse_status/index_status 由下游实际处理结果决定。HTTP 返回成功不必然意味着 indexed，UI 必须展示真实状态。路由不接受 visibility/source/owner 参数，普通用户不能通过这些接口创建公共知识。
2 MiB 字节限制与 20 万字符上限是不同维度；直接文本入口以字符上限为第一层，ingest 继续应用解析策略。PDF 文件类型检查、扫描/加密/空白等失败在解析层处理。

## 验证与修改注意

RAG 测试验证真正摄取、可见性与引用，UI 测试/前端文档页验证失败索引不显示成功。修改上传资源管理必须保留 finally.close，不能将全部未限长文件先读入内存。

## 相关源码说明

- [backend/app/rag/parsing.py](../rag/parsing.py.md)
- [backend/app/services/knowledge.py](../services/knowledge.py.md)
- [backend/tests/integration/test_rag.py](../../tests/integration/test_rag.py.md)
- [frontend/src/components/Documents.tsx](../../../frontend/src/components/Documents.tsx.md)

