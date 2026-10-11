- 对应源码：`backend/app/models/demo.py`
- 核对日期：2026-10-04
- 阅读源码：[demo.py](../../../../backend/app/models/demo.py)
- 所属目录：[目录说明](README.md)

# 明确标识的本地演示回显模型

## 定位与设计目的

DemoChatModel 继承 BaseChatModel，用于无需网络、密钥和真实模型的启动链路验证。它不是工具规划器，也不是健康推理模型。

## 关键方法与输出

bind_tools 接收框架绑定请求后直接返回 self，因此图能正常装配工具，但模型不会产生 tool_calls。_llm_type 固定 health-agent-fake。
_generate 从后向前找最后一条 HumanMessage，取其内容字符串前 80 字符，返回带“FAKE 演示模式”标记的 AIMessage。文本明确说明只是本地 LangGraph 验证、并非真实医学回答、不会自动理解或执行健康工具。_agenerate 直接复用同步实现，无持久化内部对话状态。

## 调用与能力边界

factory 在 model_mode=fake 时创建它并 cache=False；仍由真实 LangGraph、会话服务、checkpoint 和 Trace 包装运行。前端记录表单、文档摄取、偏好接口不依赖模型规划，所以这些业务仍能真实工作。
该类未实现专门的逐 token _astream；流式框架可能按基础模型适配方式暴露消息，不能据此声称本地模型有真实增量推理。测试中能确定性调用工具的 ToolChatModel/DelegatingModel 位于 tests，不是本文件演示功能。

## 验证与修改注意

test_model_factory 保证 fake 不构建 provider；test_api 验证明确标识和实际回显。增强演示行为时保留诚实标识，不要让固定示例内容看起来像当前用户真实健康记录。

## 相关源码说明

- [backend/app/models/factory.py](factory.py.md)
- [backend/tests/fakes.py](../../tests/fakes.py.md)
- [backend/tests/unit/test_model_factory.py](../../tests/unit/test_model_factory.py.md)
- [backend/tests/integration/test_api.py](../../tests/integration/test_api.py.md)

