- 对应源码：`backend/app/agents/lead_agent.py`
- 核对日期：2026-10-04
- 阅读源码：[lead_agent.py](../../../../backend/app/agents/lead_agent.py)
- 所属目录：[目录说明](README.md)

# 主健康 Agent 的框架组装

## 定位与设计目的

build_lead_agent 返回 CompiledStateGraph，使用 langchain.agents.create_agent 公开接口组装 Lead，而非自建 Agent 循环。应用入口把模型、真实健康工具、checkpointer、Memory 中间件和 Settings 传进来。

## 输入与装配顺序

model 是 BaseChatModel；tools、checkpointer、额外 middleware 可选；max_tool_calls 默认 12；settings 可选以便基础测试单独构图。
首先复制 tools 列表，避免直接修改调用者原列表。只有“已有基础工具、提供 Settings、subagents_enabled 为真”同时满足时，才创建 SpecialistPool 并追加 delegate_health_task。
配置存在时，模型侧首先加入 HealthSafetyMiddleware 和 SharedModelBudgetMiddleware。工具存在时，依次组装 ToolBoundaryMiddleware、可选 BoundedReadRetryMiddleware、ToolCallLimitMiddleware；最后追加传入的其他 middleware。图使用 HEALTH_SYSTEM_PROMPT、RunContext schema，名字为 health_lead_agent。

## 各依赖的职责

checkpointer 由外部生命周期管理；此函数不自行创建数据库。max_tool_calls 控制框架单图工具限制，Settings 构建的 RunContext.budget 还提供跨主子图的共享限制，两者并存。
SpecialistPool 使用追加委派工具前的基础工具副本建立 allowlist，所以子图不会继承该委派工具。设置关闭子 Agent 时，主图仍保留原健康工具。

## 能力与边界

函数只是构图，不会立刻调用模型或执行工具。它不验证 provider 凭据，也不负责 HTTP 身份认证。传入 settings=None 的基础测试图没有配置驱动的共享预算/紧急规则/读取重试，不能把该测试构建形式当生产配置等价物。

## 验证与修改注意

test_runtime 验证真实图与可信 context；test_provider_transport 验证实际 SDK 能看到基础工具和委派 schema；test_subagents 验证专业工具集合限制。调整中间件顺序可能改变错误归一化、重试范围和紧急短路行为，需围绕真实框架测试。

## 相关源码说明

- [backend/app/main.py](../main.py.md)
- [backend/app/agents/prompts.py](prompts.py.md)
- [backend/app/agents/subagents.py](subagents.py.md)
- [backend/app/agent/reliability.py](../agent/reliability.py.md)
- [backend/app/agent/tool_middleware.py](../agent/tool_middleware.py.md)
- [backend/tests/unit/test_runtime.py](../../tests/unit/test_runtime.py.md)

