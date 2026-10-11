# HEALTH_AGENT_SPEC.md：原始项目规范与阶段目标

- 对应源码：`HEALTH_AGENT_SPEC.md`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[HEALTH_AGENT_SPEC.md](../HEALTH_AGENT_SPEC.md)

## 文件定位

该文件是从 DeerFlow 参考目录保留的项目开发规范副本，定义系统要解决什么问题、有哪些分层约束以及 Phase 0–12 的路线。它是目标和验收依据，不能用里面的推荐目录断言所有模块已经存在。当前实现到 Phase 10，以源码与各阶段交付记录解释具体落点。

## 内容分区

| 原章节 | 阅读目的 |
| --- | --- |
| 1–7 | 定位、最终目标、独立性原则、技术栈、参考架构和 DeerFlow 阅读对象 |
| 8–11 | 健康领域层、五类基础数据、九个工具、统一 ToolResult |
| 12–13 | 工具重试与 Agent 改变策略的区别，步骤/调用/重复保护 |
| 14–16 | 公共/私人 RAG、偏好与健康事实分离、Lead/专业 Agent 分工 |
| 17–21 | Skill、guardrail、thread/checkpoint、流协议与观测目标 |
| 22–27 | Benchmark case、判分、指标、失败分类与迭代优化闭环 |
| 28–31 | 开发阶段、测试要求、编码工作规则、每阶段七段交付格式 |
| 32–33 | 最初 Phase 0 任务边界与项目核心叙事 |

## 当前如何对应到代码

数据模型位于 persistence/models.py，业务校验在 domain/schemas.py；执行机制位于 agent，角色在 agents。Memory 和 RAG 已按真实需求合并为小型模块，向量保存在 SQLite。三个专业角色共用 subagents.py；前端采用 React/Vite 并由 FastAPI 同源托管，不机械照搬参考技术树。

Phase 0 是参考分析，1 是骨架，2 工具，3 持久会话，4 流，5 RAG，6 偏好，7 多 Agent，8 可靠性，9 工作台，10 Trace。Phase 11 Benchmark 与 12 评测优化尚未由当前工程交付；规范提到的完整 Skill 体系也不能由目录示意推断已实现。

规范副本一致性由 [verify_delivery.py](backend/scripts/verify_delivery.py.md) 与 [参考快照](docs/reference-snapshot.json.md) 关联核对。除非明确更新规范来源，不应把当前实现细节反向改写进原始规范；解释差异应放在架构、交付或这套源码说明中。
