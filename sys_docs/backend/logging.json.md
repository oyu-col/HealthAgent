# logging.json：应用与 Uvicorn 的日志配置

- 对应源码：`backend/logging.json`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[logging.json](../../backend/logging.json)

这是传给 Uvicorn --log-config 的 Python logging dictConfig，version=1，disable_existing_loggers=false。标准 formatter 仅输出级别、logger 名称和 message，console handler 写 stderr。

health_agent 与 uvicorn logger 使用 INFO 且关闭传播，避免再被 root 重复输出；root 为 WARNING。uvicorn.access 无 handlers、设为 WARNING 且不传播，用于关闭通常的访问日志输出。这个设置需要启动命令实际加载文件才会生效；仅把 JSON 放在目录里不会自动配置 Uvicorn。

应用 Runtime/错误边界仅记录固定事件及服务端标识，原始健康输入、工具参数或异常不应被拼入 message。配置文件本身不是通用脱敏过滤器，无法自动擦除未来开发者主动记录的敏感文本，也不替代 [TraceRecorder](app/observability/recorder.py.md) 的结构化白名单。

关联：[应用入口](app/main.py.md)、[真实 smoke](scripts/smoke.py.md)。新增 logger 或提高调试级别时，必须核对实际输出内容和异常路径。
