# main.py：应用装配与资源生命周期

- 对应源码：`backend/app/main.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[main.py](../../../backend/app/main.py)

## 为什么把装配集中在这里

`create_app(*, settings=None, model=None, frontend_dist=None)` 是 FastAPI 工厂。它将配置、存储、模型、工具、图与业务服务组装成可运行应用。测试可以注入 Settings、BaseChatModel 及静态资源目录，生产启动则使用项目配置。模块 import 本身不会创建模型网络连接；调用 factory 时解析配置，进入 lifespan 时才初始化长期资源。

## lifespan 的初始化顺序

1. 使用 `database_session(data_dir)` 建立业务数据库会话工厂并放到 app.state。
2. 创建 TraceRepository 并执行 initialize，处理遗留运行状态；Trace 存储初始化失败会阻止应用以完整能力启动。
3. 装配 HealthRepository/HealthService 和 MemoryRepository/MemoryService。
4. 进入 embedding_session，再构造 KnowledgeRepository/KnowledgeService。
5. 用官方 AsyncSqliteSaver 打开独立 `checkpoints.db` 并 setup。
6. 接受外部注入 model，或者进入 model_session 创建本应用拥有的模型客户端。
7. 汇合健康工具、知识检索工具、PreferenceMemoryMiddleware、checkpointer 及 Settings，交给 build_lead_agent。
8. 将构建好的图和 TraceRepository 放入 HealthAgentRuntime，再装配 ThreadService。

AsyncExitStack 负责逆序释放成功进入的资源。中途创建失败时，之前已打开的连接仍会退出；停止时先撤销 runtime 可用状态，再释放客户端、saver 和数据库。外部注入模型由调用方拥有，不擅自关闭测试/上层共享模型。

## HTTP 统一边界

`request_identity` 为每个 HTTP 请求生成服务端 UUID trace_id，不信任客户端指定值。响应附 `X-Trace-ID` 和 `Cache-Control: no-store`，降低身份数据被浏览器或代理缓存的风险。未处理异常只生成固定错误及固定日志，不向响应回显原异常。

`error_response` 组装 ErrorResponse/ErrorDetail，统一 code、message、trace_id，必要时从 request.state 补 thread_id/request_id，便于客户端恢复。AgentError 使用业务指定状态；RequestValidationError 统一为安全的 422；HTTPException 保留状态但使用受控消息。HTTP 层错误和已经开始的 SSE 流内 run.failed 是不同通道，后者由流路由负责。

## 路由与 UI

工厂注册 chat、threads、stream、documents、memory、records、session、traces 路由。/healthz 在 chat 路由模块中定义，表示服务启动状态，不进行模型探测。

默认前端位置是项目根 `frontend/dist`。factory 检测到 index.html 后才注册根路径文件响应；存在 assets 目录时挂载 /assets。检测在工厂创建时执行，故一般先 build 前端再启动后端。没有通配 SPA fallback，API 404 不会被替换为 HTML；客户端采用 hash 导航避免深层页面刷新问题。

## 修改时关注什么

增加 Service 应先明确拥有者和关闭顺序，再接入 lifespan；新增路由应继续使用统一身份与异常边界。不要在模块顶层打开数据库，不要让静态页面捕获任意未知 API。当前业务库、checkpoints.db 和 Trace 终态之间不存在一个全局事务。

关联说明：[配置](config.py.md)、[依赖注入](dependencies.py.md)、[ThreadService](services/threads.py.md)、[模型工厂](models/factory.py.md)。验证入口包括 [API 集成](../tests/integration/test_api.py.md)、[UI API](../tests/integration/test_ui_api.py.md)、[模型生命周期单测](../tests/unit/test_model_factory.py.md) 和 [真实启动 smoke](../scripts/smoke.py.md)。
