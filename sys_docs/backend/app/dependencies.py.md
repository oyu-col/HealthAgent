# dependencies.py：FastAPI 资源依赖入口

- 对应源码：`backend/app/dependencies.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[dependencies.py](../../../backend/app/dependencies.py)

`get_settings(request)` 返回 request.app.state.settings；`get_runtime(request)` 读取当前应用 lifespan 中装配的 runtime。运行资源不存在或已经撤销时，后者抛出 `AgentError("not_ready", …, 503)`，让统一异常处理生成可识别响应，而不是泄漏 AttributeError。

`SettingsDependency` 和 `RuntimeDependency` 是 Annotated/Depends 类型别名。它们将“如何取得共享资源”与路由业务分开，可被 FastAPI 测试覆盖。这些依赖不会为每个请求重新创建模型、数据库或图，也不负责关闭资源；所有权在 [main.py](main.py.md) 的 lifespan。

当前模块没有通用 Service 容器或自动按类型发现机制。需要新增服务依赖时，应保持与 app.state 初始化顺序一致，并明确不可用时的语义；不能假设 import 该模块就已经完成应用启动。身份验证另见 [auth.py](auth.py.md)。
