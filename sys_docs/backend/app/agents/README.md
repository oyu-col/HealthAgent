- 对应目录：`backend/app/agents/`
- 核对日期：2026-10-04
- 实际目录：[agents/](../../../../backend/app/agents/)
- 上级说明：[目录说明](../README.md)

# 健康领域主 Agent 与专业角色层

## 定位：解决“谁负责什么”

本目录定义主健康助手、专业子 Agent 及公共提示词。使用 LangChain create_agent 构图；具体执行保护从 agent 包复用，工具从 tools 传入，模型从 models 注入。

## 当前角色组织

Lead 直接处理简单保存与查询，复杂只读分析可调用唯一委派工具 delegate_health_task。nutrition 读饮食与知识，record 读指标/运动/趋势，research 查私人文档与公共知识。专业图没有写工具、委派工具或持久 checkpointer，不继承完整父会话。

## 输入输出与可信边界

主图收到 HumanMessage 和可信 RunContext。子图只收到必要 task 字符串、服务端传递身份/预算及追踪回调；返回 SpecialistReport，含终态 summary 和真实工具 observations。子报告仍是待核对的数据，不能更改规则，也不能因 status=completed 就声称所有工具都成功。
提示词表达健康行为准则，代码 allowlist、用户过滤、严格 schema 和共享预算才是实际权限边界。真实 provider 是否会正确选择委派和汇总，当前离线测试没有证明。

## 装配与修改注意

lead_agent.py 是构图入口，只有 tools、settings 和 subagents_enabled 同时满足才增加委派。subagents.py 中修改角色工具集合会改变能力边界；prompts.py 中修改文案会改变模型行为，须与实际工具能力同步，不能承诺未实现的删除/诊断能力。

## 阅读与验证

先读 lead_agent，再看 prompts 和 subagents。test_subagents 验证三角色权限/上下文/预算/取消；test_provider_transport 检查实际 SDK 导出的工具 schema；test_reliability 覆盖规则短路和失败保护。fake 演示模型并不会因这些角色已注册就自主委派。

## 文件导航

- [__init__.py](__init__.py.md)：健康领域 Agent 角色包。
- [lead_agent.py](lead_agent.py.md)：主健康 Agent 的框架组装。
- [prompts.py](prompts.py.md)：健康助手系统提示词与业务行为规则。
- [subagents.py](subagents.py.md)：受限专业子 Agent 与委派工具。

