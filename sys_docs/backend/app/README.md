# app：应用实现与分层边界

- 对应目录：`backend/app/`
- 核对日期：2026-10-04
- 实际目录：[app](../../../backend/app)

## 职责地图

| 文件或子目录 | 当前实际职责 |
| --- | --- |
| [main.py](main.py.md) | 组合根：factory、生命周期、异常边界、路由和静态页面 |
| [config.py](config.py.md) | 唯一配置契约、模式选择和启动校验 |
| [auth.py](auth.py.md) / [dependencies.py](dependencies.py.md) | 可信 owner 解析与共享资源依赖注入 |
| [api/](api/README.md) | 外部 HTTP/SSE 契约，不让客户端直接控制框架执行参数 |
| [agent/](agent/README.md) | 通用运行、预算、超时、工具错误和可靠性机制 |
| [agents/](agents/README.md) | Lead 和三个专业角色的 prompt、工具权限与图装配 |
| [models/](models/README.md) | fake/provider 模型选择及 HTTP 客户端生命周期 |
| [domain/](domain/README.md) | 输入校验与统一 ToolResult；不同于数据库 ORM |
| [tools/](tools/README.md) | 向模型暴露的健康能力和隐藏服务端 context |
| [services/](services/README.md) | 健康、文档、偏好及会话的业务编排 |
| [persistence/](persistence/README.md) | ORM、owner 过滤、事务与存储访问 |
| [rag/](rag/README.md) | 文档解析、embedding 和范围受限的向量检索 |
| [memory/](memory/README.md) | 显式偏好句式识别与临时上下文注入 |
| [observability/](observability/README.md) | 白名单事件采集、真实回调计数和脱敏执行摘要 |
| [__init__.py](__init__.py.md) | Python 包标识，无资源初始化副作用 |

## 设计上的几个区分

`agent` 是“如何运行”，`agents` 是“运行哪个角色”。`models` 表示聊天模型适配器，数据库模型实际位于 persistence/models.py。API schemas 服务于请求/响应，domain schemas 服务于业务数据；不能把 HTTP DTO、模型工具参数和 ORM 当成可互换对象。

主要依赖方向为 API → Service/Runtime → Tool → Service → Repository。Repository 不读取 HTTP 请求来决定 owner；可信身份在服务端解析后沿参数/context 传入。Tool schema 隐藏用户和执行标识，模型不能自行授予权限。

## 请求与资源

每个应用 lifespan 共享数据库连接工厂、模型客户端和构建好的图；每次运行具有独立的可信 RunContext、预算和 Trace。会话历史交给官方 checkpoint，长期业务数据交给 Repository，浏览器只接收允许公开的可见消息与协议事件。共享资源不等于共享不同用户的消息或权限。

阅读顺序建议从 main.py 找装配点，再选择一个 API 跟到 Service/Repository，最后阅读对应集成测试以理解失败语义。目录不是为了满足规范树而机械拆空文件，当前合并实现以实际代码为准。
