# Phase 7–10 实施与验收计划

本次按 HEALTH_AGENT_SPEC.md 第 28 节推进到 Phase 10，并根据用户要求重点参考 DeerFlow UI。已有 Phase 0–6 后端继续复用；新 UI 提前开始的工作并入 Phase 9。Phase 11 Benchmark / Phase 12 优化不在本次范围。

## Phase 7 — Multi-Agent

- Lead 保留直接调用健康工具的路径，复杂任务才通过显式工具委派 Nutrition / Record / Research。
- 专业 Agent 使用框架 create_agent，只有对应只读工具，无递归委派、写入或任意执行权限。
- 身份与执行预算来自可信 RunContext；委派上下文独立，结果作为数据交给 Lead 汇总。
- 验证角色工具范围、真实数据库 owner 过滤、结果汇总、总预算、并发、超时与取消。

## Phase 8 — Reliability

- 在已有总超时、checkpoint、幂等写入、最大步骤和重复检测上补齐有限只读重试及工具超时。
- 区分模型 SDK 重试、工具重试和 Agent 根据失败重新规划；永久错误不重试，写入结果不确定时不盲重放。
- 对明确高风险自述进行保守短路；模型输出不能被视为临床验证。
- 用故障注入验证瞬态失败、写超时、取消传播、参数错误和共享预算。

## Phase 9 — Frontend

- 独立 React / TypeScript / Vite 工作空间，参考 DeerFlow 侧栏、会话列表、居中对话、输入框、资料侧面板与偏好卡片。
- 实现 Chat、Thread、Streaming、Documents、Health Records；同时提供 Memory 管理和 Trace 查看。
- 同源 FastAPI API；凭据仅存当前页面内存；更换身份清空工作空间、取消请求；Markdown 不执行 HTML 或自动加载远程图片。
- 增量 SSE 解析覆盖 UTF-8 分片，最终回答只认权威终态；EOF 保留 request_id 并通过 checkpoint 恢复。
- 验证单元测试、TypeScript、Lint、生产构建、合成 API 浏览器用例、真实 Uvicorn / SQLite 浏览器 smoke，以及桌面/手机目视检查。

## Phase 10 — Trace / Observability

- 记录真实 model/tool/委派步骤、可观测重试、耗时、token usage 和终止原因，缺失指标明确标注不可观测。
- 持久化按 owner 隔离；保留有界事件与 trace 数量；不保存健康问题、工具参数和结果原文。
- 失败、取消、恢复、缓存回放分别记录；通过最近回答的执行记录弹窗查看时间线。
- 验证数据持久化、用户隔离、失败恢复、SSE、取消、隐私字段、存储失败和保留上限。

## 交付与边界

每阶段记录 Completed、Files Changed、Design、DeerFlow Reference、Tests、Known Issues、Next Phase。最终更新 README、架构和机器可读验收记录。所有测试指标来自执行结果；fake / 合成模型验证工程行为，不代表真实模型医疗质量或领域 Benchmark。
