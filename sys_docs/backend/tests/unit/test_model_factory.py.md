- 对应源码：`backend/tests/unit/test_model_factory.py`
- 核对日期：2026-10-04
- 阅读源码：[test_model_factory.py](../../../../backend/tests/unit/test_model_factory.py)
- 所属目录：[目录说明](README.md)

# 模型选择与 HTTP 客户端清理测试

## 测试目的

验证 model_session 的资源所有权和配置隔离，避免 fake 模式意外初始化真实 provider、真实模式读取无关环境或启动失败泄露 HTTP 连接。

## 三个测试及断言

1. test_fake_never_initializes_provider：把工厂模块中的 ChatOpenAI 替换成“一调用就失败”的函数，进入 fake session 后仍得到 DemoChatModel，证明 fake 分支没有构造 provider。
2. test_provider_explicit_configuration_and_cleanup：先设置错误的 OPENAI_API_KEY/OPENAI_BASE_URL，再用明确合成 Settings 构造真实 ChatOpenAI 对象；断言 model_name、key、base_url、max_retries、timeout 都来自 Settings，streaming 没被硬编码；上下文内客户端未关闭，退出后同步/异步客户端都关闭。
3. test_clients_close_if_provider_construction_fails：monkeypatch 一个会抛异常的 ChatOpenAI 构造器并记录传入客户端；断言不 yield 模型，且两个客户端仍被上下文关闭。

## 输入、执行与边界

使用 httpx 客户端与真实适配类，但不发送模型请求。合成 key 和 example.invalid 用于断言，不是可用配置。测试成功只证明构造与生命周期，不证明远端模型、网络连通性或 Chat Completions 兼容性。

## 修改注意

修改 provider 适配、增加客户端参数或改为每请求实例时，都需重新审视清理职责。不要删除构造失败分支测试；资源泄漏常发生在 lifespan 尚未 yield 的启动阶段。实际请求协议由 test_provider_transport 覆盖。

## 相关源码说明

- [backend/app/models/factory.py](../../app/models/factory.py.md)
- [backend/app/models/demo.py](../../app/models/demo.py.md)
- [backend/tests/integration/test_provider_transport.py](../integration/test_provider_transport.py.md)

