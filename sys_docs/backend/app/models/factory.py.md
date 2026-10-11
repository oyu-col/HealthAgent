- 对应源码：`backend/app/models/factory.py`
- 核对日期：2026-10-04
- 阅读源码：[factory.py](../../../../backend/app/models/factory.py)
- 所属目录：[目录说明](README.md)

# 模型工厂与 provider HTTP 客户端生命周期

## 定位与设计目的

model_session(settings) 是 asynccontextmanager，向应用 lifespan 提供 BaseChatModel，并拥有 provider 同步/异步 HTTP 客户端。模块导入时不联网，工厂不读取浏览器 token。

## 两条实际路径

fake：yield DemoChatModel(cache=False) 后返回，不构造 ChatOpenAI 或 provider HTTP 客户端。
provider：先进入 httpx.Client，再进入 httpx.AsyncClient，均使用 model_timeout_seconds；用显式 Settings 字段构造 ChatOpenAI，设置 model、api_key、base_url、timeout、max_retries，传入两个客户端，use_responses_api=False，cache=False。

## 配置与接口选择

Settings 已完成模式、必填 provider 字段、URL 和范围验证；工厂不会暗中继承无关 OPENAI_API_KEY/OPENAI_BASE_URL。当前走兼容 Chat Completions 的适配路径，不使用 Responses API。
不固定 streaming 字段，允许图回调和 astream 调用选择相应传输方式。model_max_retries 是 SDK 层重试，与工具中间件只读重试不同，也不等同于 Trace 能观察到的网络尝试数。

## 资源、错误与取消边界

嵌套上下文保证正常结束或模型构造失败时两个 HTTP 客户端都关闭。应用 lifespan 负责进入和退出 model_session；请求 Runtime 使用模型，但不应每次自行关闭这些共享客户端。
工厂不捕获 provider 运行错误来改用 fake；错误在 Runtime 映射为安全的失败。连接建立/模型初始化和实际请求是否联网仍取决于调用时机，不应把“构造成功”称为已验证远端可用。

## 验证与修改注意

test_model_factory 验证显式配置不会被外部环境污染，以及正常/构造失败都关闭客户端。test_provider_transport 用真实 ChatOpenAI SDK 加本地 MockTransport 验证普通、工具和流式协议；该测试不连接真实模型服务。

## 相关源码说明

- [backend/app/main.py](../main.py.md)
- [backend/app/config.py](../config.py.md)
- [backend/app/models/demo.py](demo.py.md)
- [backend/tests/unit/test_model_factory.py](../../tests/unit/test_model_factory.py.md)
- [backend/tests/integration/test_provider_transport.py](../../tests/integration/test_provider_transport.py.md)

