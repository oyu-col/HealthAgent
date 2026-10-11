# smoke_server.py：支持优雅关闭的 smoke 服务

- 对应源码：`backend/scripts/smoke_server.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[smoke_server.py](../../../backend/scripts/smoke_server.py)

serve(port, signal_path) 构造 loopback Uvicorn Server，factory 指向 app.main:create_app，读取 logging.json。内嵌 shutdown_signal 异步循环每 0.1 秒通过 asyncio.to_thread 检查 stop 文件；文件出现时设置 server.should_exit，让 FastAPI lifespan 正常退出并关闭 SQLite/客户端。

服务退出的 finally 取消 watcher 并 gather(return_exceptions=True)，避免遗留等待任务。Windows 虚拟环境 launcher 与真实 Python 进程可能不同，仅终止 launcher 不一定释放底层数据库；文件信号关闭使 smoke 能等待真正的应用清理。

CLI 从 argv 读取端口和信号路径，解析后的路径必须在 backend 内且父目录名以 .smoke- 开头，否则拒绝。这个限制防止测试 runner 被误用为监听任意文件的常驻管理服务。

本脚本只由 [smoke.py](smoke.py.md) 的临时流程使用，不提供公共 shutdown HTTP API，也不是生产进程管理器。配置和数据目录由父进程环境传入；实际生命周期仍由 [main.py](../app/main.py.md) 管理。
