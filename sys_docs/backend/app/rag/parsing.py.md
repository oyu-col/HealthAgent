# parsing.py：文档校验与可追溯分块

- 对应源码：`backend/app/rag/parsing.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/rag/parsing.py) · [目录说明](README.md)

## 接口和校验

validate_filename(filename) 拒绝空名称、超过 200 字符、路径分隔符/反斜杠/冒号/NUL/换行，仅允许 .txt/.md/.pdf（扩展名不区分大小写）。返回原名称，不会把任意用户路径当作本机文件读取。

parse_and_split(filename,content:bytes) 重复检查文件名和大小，content 必须非空且 ≤MAX_BYTES=2×1024×1024。它从传入内存 bytes 解析，不负责上传流、数据库或磁盘原文件存储。

## TXT / MD 和 PDF

文本按 utf-8-sig 解码，允许 UTF-8 BOM，最多 MAX_CHARS=200000 字符，整篇视为 page=1。Markdown 作为文本处理，不渲染 HTML，也不根据标题建立独立结构树。

PDF 使用 PdfReader(BytesIO(content),strict=True)，拒绝加密文档和超过 50 页；逐页 extract_text，页码从 1 开始，累计文本不得超 20 万字符。pypdf 日志级别设为 CRITICAL，降低损坏文档诊断泄露原始头部字节的风险；该日志设置是进程全局副作用。

所有页都无非空文字则抛 ValueError，错误含义是“无可提取文本，不支持 OCR”。空白/纯扫描 PDF 不会凭空识别出文字。

## 分块输出

RecursiveCharacterTextSplitter 使用 chunk_size=600、chunk_overlap=80、add_start_index=True，按双换行、换行、中文句号/叹号/问号、英文句号、空格、字符回退逐级切分。每个 LangChain Document 含 page_content 和 metadata.page/start_index；start_index 是对应页文本内的字符位置，不是 PDF 字节偏移。

超过 500 个片段失败。chunk_size 是字符切分目标，不等价于 600 个模型 token；页码和偏移用于提供引用出处，文本提取的阅读顺序仍受 PDF 本身编码影响。

## 调用、错误与测试

[KnowledgeService](../services/knowledge.py.md) 用 asyncio.to_thread 执行此同步函数，捕获解析异常后发布 parse_failed 状态并隐藏原异常。这里不做医疗内容审核、不执行文档指令，也不加入系统 prompt。

[集成测试](../../tests/integration/test_rag.py.md) 使用程序生成的文本 PDF 验证 page=1 和内容，空白 PDF 验证失败，并测试非法路径/扩展名。改变 chunk_size、重叠或页码算法需同步 [index_version](embeddings.py.md)，否则旧向量版本会被误认为兼容。
