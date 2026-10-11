- 对应源码：`backend/tests/integration/test_api.py`
- 核对日期：2026-10-11
- 阅读源码：[test_api.py](../../../../backend/tests/integration/test_api.py)
- 所属目录：[目录说明](README.md)

# FastAPI 基础对话与安全 HTTP 契约测试

## 定位与执行方式

使用 create_app、显式 lifespan_context 和 httpx.ASGITransport，在内存 HTTP 通道中调用真实 FastAPI 路由、服务和临时持久层。通常注入 SpyChatModel，最后一项使用真实 DemoChatModel 工厂路径。

## 具体测试覆盖

- **健康探针/契约/完成响应**：/healthz 精确返回 status=ok、phase=12 与 model_mode=fake 且不调用模型；OpenAPI 存在主要路由、请求禁止额外字段且声明 ErrorResponse；普通对话返回真实生成的 run/trace UUID、completed、no-store；客户端伪造 X-Trace-ID 不被采用；lifespan 退出 runtime 被清理。
- **参数化坏请求**：缺 message、空白、数字、额外 user_id/config、非法 thread_id、超过配置或硬长度上限均为 422；模型未调用，错误不回显 private/victim。
- **格式错误与缺失路由**：非法 JSON 返回安全 422；不存在路径为 404，error.trace_id 与响应头一致。
- **独立新会话隔离**：三个并发请求加一个顺序请求均不传 thread_id，断言各自答案对应输入、run/trace 不重复、模型只看到系统+本轮用户两条消息，并使用 local-user。这里不是说同一 thread 没有历史。
- **provider 失败**：注入合成 401 SDK 错误，API 返回 provider_error/502；没有 fake 回退，也不泄露异常和健康输入。
- **实际 fake 适配器**：未注入模型时明确输出 FAKE 演示标识及输入回显。

## 设计意义与边界

从 HTTP 输入到 Runtime 再到公开响应的完整约束在此固化，防止“框架能运行”但 HTTP 合约已破坏。ASGITransport 不模拟真实 TCP 断线、代理缓冲或浏览器网络，这些需要其他传输/浏览器验证。

phase=12 是与当前响应 schema 同步的版本断言；测试没有因此执行 Benchmark，也没有将 fake 输出判为真实模型能力。特别是 provider 失败项只注入 SDK 异常，不访问在线服务。

## 修改注意

改变 phase、响应字段、全局异常处理、身份入口或构建方式时保持契约测试同步。不要把合成模型的正确回显写成自然语言健康问答效果；本文件不评测医疗事实或在线 provider。

## 相关源码说明

- [backend/app/main.py](../../app/main.py.md)
- [backend/app/api/chat.py](../../app/api/chat.py.md)
- [backend/app/api/schemas.py](../../app/api/schemas.py.md)
- [backend/tests/fakes.py](../fakes.py.md)
- [backend/tests/unit/test_runtime.py](../unit/test_runtime.py.md)

