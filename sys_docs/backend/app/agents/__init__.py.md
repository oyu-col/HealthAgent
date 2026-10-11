- 对应源码：`backend/app/agents/__init__.py`
- 核对日期：2026-10-04
- 阅读源码：[__init__.py](../../../../backend/app/agents/__init__.py)
- 所属目录：[目录说明](README.md)

# 健康领域 Agent 角色包

## 当前内容与定位

仅包含 `Health-domain agent definitions.` 包级说明。此文件不创建模型、工具或子 Agent，不注册 API，也没有生命周期副作用。
角色装配位于 lead_agent.py，专业角色限制位于 subagents.py，公共健康规则文本位于 prompts.py。与同级 app/agent 的区别是：本包定义“谁负责什么”，后者定义“如何执行并可靠停止”。

## 修改注意

保持包导入轻量；不要在初始化时读取用户数据或建立 provider 客户端。新角色应通过明确的构建器和 allowlist 引入。

## 相关源码说明

- [backend/app/agents/lead_agent.py](lead_agent.py.md)
- [backend/app/agents/subagents.py](subagents.py.md)
- [backend/app/agent/runtime.py](../agent/runtime.py.md)

