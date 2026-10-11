# 显式启用的真实模型供应商连通性测试

- 对应源码：`backend/tests/live/test_provider.py`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../backend/tests/live/test_provider.py) · [本目录说明](README.md)

## 测试目的

test_live_provider_smoke 使用当前有效配置建立真正的 model_session，构建 Lead Agent 与 HealthAgentRuntime，发送一句不要求医疗建议的介绍请求。它验证真实供应商调用能够返回非空文本，并且结果不是 fake 模型的演示回显。

该函数带 pytest.mark.live。默认测试收集由测试配置约定跳过 live，只有显式 --run-live 才允许尝试；本文件自身还会在 load_settings 抛 RuntimeError 或 model_mode 不为 provider 时 pytest.skip。加载失败被跳过并不等于真实连接成功。

## 调用链

1. load_settings 读取当前项目配置。
2. async with model_session(settings) as model，明确拥有模型 HTTP 资源生命周期。
3. build_lead_agent(model) 创建框架 Agent；HealthAgentRuntime 接入运行限制。
4. RunContext.create(settings, "live-smoke") 构造本次执行上下文。
5. ainvoke 发送“请用一句话介绍你能提供的帮助，不要给出具体医疗建议。”
6. 断言 answer.strip() 非空，且不包含 “[FAKE 演示模式]”。

测试没有创建真实用户健康记录，不需要提交病史或文档；它仍会访问配置的外部模型服务，并可能产生供应商费用。

## 能验证与不能验证的内容

它是连接/适配/简单推理冒烟检查，不测试完整 FastAPI 路由、SSE、数据库、RAG 检索、专业 Agent、正确工具参数或医学质量。配置缺失时的 skip 是明确未执行状态，不应计作模型验证通过。

本文仅根据源码说明；本次 sys_docs 文档工作未运行该测试、未读取或复制任何配置密钥。

相关说明：[本目录索引](README.md)、[前端真实接口但 fake 模型联调](../../../frontend/scripts/smoke.mjs.md)。

