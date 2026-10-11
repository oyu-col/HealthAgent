- 对应源码：`backend/app/agent/__init__.py`
- 核对日期：2026-10-04
- 阅读源码：[__init__.py](../../../../backend/app/agent/__init__.py)
- 所属目录：[目录说明](README.md)

# 执行机制包入口

## 当前作用

文件只有包级说明 `Framework invocation and trusted per-request context.`。它标记 `app.agent` 的职责是框架调用和可信请求上下文，不做实例化、注册或 I/O。

## 目录区分

`agent` 是通用执行机制：Runtime、上下文、预算和工具保护；`agents` 是健康领域角色：Lead、专业子 Agent 和提示词。这里没有重新实现 LangGraph 的调度循环。阅读具体行为应从 runtime.py 进入。

## 相关源码说明

- [backend/app/agent/runtime.py](runtime.py.md)
- [backend/app/agents/lead_agent.py](../agents/lead_agent.py.md)

