- 对应源码：`backend/tests/integration/test_provider_transport.py`
- 核对日期：2026-10-04
- 阅读源码：[test_provider_transport.py](../../../../backend/tests/integration/test_provider_transport.py)
- 所属目录：[目录说明](README.md)

# 真实 ChatOpenAI SDK 的本地协议集成测试

## 测试目的与方法

用真实 ChatOpenAI/SDK 和真实 LangGraph，底层 HTTP 替换为 httpx.MockTransport。这样能够验证请求序列化、工具回传与流式解析，而不用真实网络、计费凭据或随机模型输出。

## 三个完整链路

1. **test_actual_sdk_tool_call_and_observation**：首次 mock 响应返回 add_health_metric 工具调用及嵌套 record JSON；真实工具把合成体重写入 SQLite。第二次 provider 请求必须以 tool 角色消息结尾，解析其 content 后 success=true；模拟 provider 再返回终态答案。最后断言两次模型 HTTP 调用、API 正确答案、数据库仅 1 条记录。
2. **test_actual_sdk_streaming_is_incremental**：断言 provider 请求 stream=true，返回真实 Chat Completions chunk 格式的两个中文片段及 stop/[DONE]。调用 /api/chat/stream 后用 SSEDecoder 检查 message.delta 依次为“合成”“中文流”，completed.answer 为完整拼接。
3. **test_chatopenai_request_and_answer_through_real_graph**：provider 模式的显式 Settings 和合成 key；断言实际 SDK 请求路径 /v1/chat/completions、Authorization、模型名、最后 user 消息与首条 system 提示；工具列表为 10 项且有 delegate_health_task、没有 user_id schema；HTTP 响应不含密钥。

## 为什么它与 fake 测试不同

SpyChatModel 可以绕过 SDK 序列化细节，本文件则穿过真正适配器，能发现工具 schema、content 类型、版本或 streaming 兼容问题。但响应全部由测试函数生成，仍然不能说明线上模型会选对工具、给出正确医学回答或支持当前功能。

## 资源与维护

同步/异步 mock 客户端和应用 lifespan 都显式关闭。新增/删减基础工具会改变固定工具数量断言，需确认委派开关和隐藏身份仍满足预期；切换 provider API 路径或升级 SDK 时应优先运行此集成文件。这里不会触发 --run-live 真实服务测试。

## 相关源码说明

- [backend/app/models/factory.py](../../app/models/factory.py.md)
- [backend/app/agents/lead_agent.py](../../app/agents/lead_agent.py.md)
- [backend/app/api/stream.py](../../app/api/stream.py.md)
- [backend/app/api/sse.py](../../app/api/sse.py.md)
- [backend/tests/unit/test_model_factory.py](../unit/test_model_factory.py.md)

