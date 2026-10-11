# scripts：运维入口和真实启动验证

- 对应目录：`backend/scripts/`
- 核对日期：2026-10-04
- 实际目录：[scripts](../../../backend/scripts)

这些脚本复用正式 app 模块，不是另一套业务实现。从 backend 工程环境启动，以确保 app 包和依赖已安装。

| 脚本 | 用途与副作用 |
| --- | --- |
| [ingest_public.py](ingest_public.py.md) | 管理员审核后将文件导入公共知识域；写业务数据库，provider embedding 时可联网 |
| [stream_client.py](stream_client.py.md) | POST 对话并增量解析 SSE；会创建/继续真实会话 |
| [smoke.py](smoke.py.md) | 启动自有临时 Uvicorn，验证真实 HTTP/SQLite，可选 Chromium UI，然后关闭清理 |
| [smoke_server.py](smoke_server.py.md) | smoke 专用 runner，监听临时目录 stop 文件进行优雅关闭 |
| [verify_delivery.py](verify_delivery.py.md) | 核对参考文件哈希、规范副本、原交付文档链接及阶段章节 |

smoke 使用合成输入、临时数据库与 fake 配置；ingest_public 和 stream_client 则操作所选真实服务/数据。不能把 smoke 的成功理解为 provider 模型质量已验证，也不应把普通导入脚本当成无副作用的检查命令。

本套 sys_docs 的覆盖和链接由独立 [_meta/check-docs.mjs](../../_meta/check-docs.mjs) 验证，原 verify_delivery.py 没有递归检查新增说明目录。
