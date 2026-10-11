# Phase 1 计划：最小可运行 Agent 的验收定义

- 对应源码：`docs/phase-1-plan.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-1-plan.md](../../docs/phase-1-plan.md)

这份计划保留实施前的范围、依赖选择、拟新增文件、配置契约、HTTP/Runtime、测试和交付顺序；开头说明 Phase 1 已完成，实际结果看 [Phase 1 交付](phase-1-delivery.md.md)。

关键设计是先用独立 Python/FastAPI 工程运行真实 create_agent 图，fake 与 provider 走同一 Runtime，公开 context 传可信身份，设置输入/超时/步骤预算，并让测试可以注入模型和关闭客户端。计划明确不先实现数据库、持久会话、SSE、RAG、Memory、SubAgent 或 UI。

阅读时要区分历史接口：当时 chat 只接 message、每次独立；当前已经支持 thread_id/request_id 和持久恢复。计划里的“拟采用依赖”“将来执行命令”不是当时已安装/已通过，也不能替代当前 uv.lock。

它适合解释为何分阶段建立可验收骨架。修改现有功能应参照当前 [API](../backend/app/api/README.md) 与 [Runtime](../backend/app/agent/README.md)，不要为了保持旧计划而回退后续已交付能力。
