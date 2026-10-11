# architecture.md：现状、目标和架构取舍

- 对应源码：`docs/architecture.md`
- 核对日期：2026-10-11
- 目录导航：[docs](README.md)
- 原文件：[architecture.md](../../docs/architecture.md)

## 本文承担的角色

原文以当前 Phase 12工程落地摘要开头，明确在线provider未完成验收，随后保留最终目标目录、分层、RAG/Memory、可靠性、流、测试和评测路线。它表达系统设计及未来扩展方向，不是从磁盘实时生成的目录树。

## 关键阅读点

当前业务、偏好、文档向量、Thread 元数据和 Trace 使用 health.db，官方 AsyncSqliteSaver 独立管理 checkpoints.db。Lead 装配九个健康/RAG 工具及可关闭委派；三个专业 Agent 受只读 allowlist、共享预算、并发和超时约束。UI 为 React/Vite，由 FastAPI 同源托管，hash 导航。

最终目标示意仍含 auth/principal.py、独立 skills/guardrails、Benchmark 等较细目录；实际代码使用 auth.py、agent/reliability.py、agents/subagents.py 等合并实现。图中的独立 vector store 抽象当前落在 SQLite JSON 向量，不能推断另有 Chroma/FAISS 服务。规范要求使用框架能力，实际可靠性优先框架 middleware，不自建无限 Agent 循环。

原文后半段将Benchmark设计与当前实现对应：29个合成案例→环境初始化→实际API/图→SQL与ToolResult/citation/Trace观察→独立grader→统计和同协议比较。contract与provider分开，空分母N/A，报告保留失败，真实连接状态另列。实际结果见Phase 11/12交付及results，不能由架构目标推断在线效果。

Phase 12新增两条边界：local_hash检索必须至少有一个相同原始词法特征，语义provider不受此限制；Trace要将每个模型/工具run_id的开始与结束配对才完整，缺失事件不补造。原索引版本与向量保持兼容，取消工具的结束回调缺口尚未消除。

## 适合何时阅读

新增跨层功能、调整数据库边界或评估是否需要拆模块时，先阅读该文件确定动机，再核对 [当前 app 地图](../backend/app/README.md)。如现状发生变化，应更新开头落地摘要并明确保留目标部分的时态，避免把历史规划与现有功能混写。
