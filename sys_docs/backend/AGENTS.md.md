# backend/AGENTS.md：后端开发与验证约定

- 对应源码：`backend/AGENTS.md`
- 核对日期：2026-10-11
- 目录导航：[本目录说明](README.md)
- 源码：[AGENTS.md](../../backend/AGENTS.md)

该文档继承项目级约束，并将后端工作具体化：独立 Python 工程、真实 LangChain/LangGraph 执行、公共框架 API、Tool→Service→Repository、可信身份和最小数据暴露。它用于约束代码修改方式，不会作为 Agent 的提示词加载。

文件要求区分业务事实、Memory、Thread 元数据、checkpoint 和 Trace，维护超时/取消/重试预算，错误不回显秘密或健康原文。测试应使用临时数据库和可注入模型，默认隔离外网；live 模型测试显式启用，fake 结果不能解释为医学性能。

它列出从 backend 目录执行 pytest、Ruff check 和 Ruff format --check 的命令，也允许使用 uv run --no-sync。行为变化应先添加能复现问题的测试，再修改实现。单独同步说明文档时仍应核对源码与链接，不能把没有执行的应用测试写成通过。

## Phase 11/12 评测约定

后端约定现在明确要求：独立 Benchmark 从本目录运行 `../benchmark/runner.py`；真实评测另外使用 `--mode provider --allow-provider`。这与 pytest 的 `--run-live` 是两个入口，不能因为其中一个开关启用就推断另一个也获得执行配置。

contract 模式中的工具决策由脚本确定，真实运行应用、工具、数据库与检索链路，但不能代表模型自然语言理解、规划或医学回答能力。比较优化前后结果必须遵守冻结的案例、配置和判分协议，不能通过修改答案或评分标准制造提升。每次运行结果还应区分真实 provider 与工程契约验证。

这些约定与既有权限边界共同生效：可信身份由服务端注入，RAG 在 SQL 层先按 owner/visibility 限定候选，子 Agent 只读且共享预算；实际模型调用次数、工具重试与 SDK 内部不可见重试不能混为一谈。本文解释开发约束，不是 Agent 的运行时提示词，也不会自动执行评测。

变更前先读项目级 [AGENTS.md](../AGENTS.md.md)，再定位对应模块和阶段目标。不要把“首版 local 单用户”误解为可公开部署的完整账户系统。
