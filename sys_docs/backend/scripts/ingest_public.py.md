# ingest_public.py：管理员公共资料导入

- 对应源码：`backend/scripts/ingest_public.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[ingest_public.py](../../../backend/scripts/ingest_public.py)

## 入口和调用链

argparse 要求本地 path 与必填 --source，后者应是真实来源 URL 或出版物标识。main 调用 asyncio.run(ingest(args))；ingest 加载 Settings，用 asyncio.to_thread 读取文件 bytes，再进入 database_session 与 embedding_session，构造正式 KnowledgeService。

实际调用为 service.ingest("system-public", path.name, content, visibility="public", source=args.source)。固定系统 owner 与明确 public 标记使这个入口成为普通私人上传以外的运维发布通道。正常 HTTP API 不授予普通用户设置 public 的权限。

## 结果和错误

脚本以 ensure_ascii=False 输出 JSON 结果；只有 index_status=indexed 才正常结束，否则 SystemExit(1)。解析、限额、embedding、去重及索引事务规则由 [KnowledgeService](../app/services/knowledge.py.md) 统一处理。资源使用异步上下文管理器关闭；此脚本没有后台任务队列或自动无限重试。

source 参数只是来源元数据，不会自动抓取 URL，也不会替管理员验证文章质量、许可或医学可靠性。provider embedding 可能将片段发送到显式配置的服务；local_hash 走本地基线。

这是有持久写入的运营命令，不是用户页面上传的快捷别名。扩展公共资料管理时，应继续隔离“谁可以发布”与“所有用户可读取公共资料”，不能直接在普通上传 schema 加开放 public 字段。
