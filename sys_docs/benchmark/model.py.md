- 对应源码：`benchmark/model.py`
- 核对日期：2026-10-11
- 阅读源码：[model.py](../../benchmark/model.py)
- 所属目录：[目录说明](README.md)

# 只用于工程契约的确定性脚本模型

## 类和框架接口

ContractModel继承LangChain BaseChatModel，提供bind_tools、_generate和_agenerate。它作为真实create_agent图的可注入模型工作，工具执行仍由框架完成，不能直接替代Service或Repository。

execution_plan是唯一任务决策输入，Pydantic字段exclude=True避免普通序列化包含整份计划。_positions以PrivateAttr保存每个角色当前动作序号；角色来自可信get_runtime().context.agent_name，而非用户输入。

## 决策顺序与可见答案

每轮按角色选择health_lead_agent、record_agent、nutrition_agent或research_agent的计划。tool动作生成真实AIMessage.tool_calls，包含name、args及由角色/位置构成的稳定call id；respond动作只发送计划明确写入的简短答复。

计划耗尽后收集当前messages里的真实ToolMessage.content，以JSON字符串列表和[CONTRACT ONLY]前缀返回。它没有读取expected_state、expected_observations或预设标准答案来宣布成功；若工具返回失败，回显中会包含失败结果。

## 设计边界

bind_tools仅满足框架绑定接口，不从schema推理可选动作；_agenerate直接调用同步_generate，不发网络请求。模型不理解中文任务、不进行医学推理，也不会因业务prompt改进而自动变聪明。

按角色保存位置可隔离一次主/子图流程，但同一角色在同一案例内多次委派会继续消耗既有序列；扩展复杂多轮案例时必须明确计划生命周期。脚本模型实例由run_case每例重新创建，不能跨案例共享位置。

## 为什么仍需要这种模式

可控计划用于复现超时、无效参数、重复调用和幂等恢复等模型未必稳定触发的边界。实际ToolResult、数据库、checkpoint和Trace让这些测试具有工程意义；固定选择不应计为模型规划成绩。

[runner集成测试](../backend/tests/integration/test_benchmark_runner.py.md)将期望数据库数量和答案marker改错后，真实工具执行/模型调用数量保持原样且判分失败，防止grader自证。对应provider模式完全不使用本类。

