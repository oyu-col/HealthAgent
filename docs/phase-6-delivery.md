# Phase 6 — Memory 与阶段总验收

## Completed

Phase 2–6 的实现闭环全部接入。Phase 6 新增长期偏好的提取、持久化、检索、临时上下文注入，以及查看、更正、删除 API。当前偏好包括回答风格、语言、饮食和运动偏好；指标、病史等客观健康信息不作为 Memory 存储。

最终验收：**95 passed / 1 skipped**（21.38 秒），Ruff 检查和 67 个 Python 文件格式检查通过，锁定依赖离线同步通过，真实 HTTP smoke 及关闭清理通过。82 个文档本地链接有效，57 个参考文件 hash 未变，规范副本字节一致。

## Files Changed

新增 `app/memory/extraction.py`、`app/memory/middleware.py`、MemoryPreference / MemoryReceipt、`persistence/memory_repository.py`、`services/memory.py`、`api/memory.py` 与集成测试。更新 RunContext、Lead Agent 装配、prompt、配置、README、AGENTS 与架构状态。smoke 扩展为真实 HTTP 会话 / SSE / 文档 / Memory 验收，增加仅供测试的优雅关闭 runner。

## Design

通过框架 abefore_agent 提取当前用户明确的保存 / 忘记请求，采用固定语法和 allowlist，不复制原始对话或健康事实。偏好在模型前入库，让本轮模型看到实际 applied_changes；这与 DeerFlow 的后台完整对话 extraction 不同，适合可解释、可离线测试的第一版。只有约定的显式句式会被自动提取，其他偏好通过管理 API 设置。

偏好按 user_id 隔离。风格 / 语言始终可用，饮食 / 运动偏好按问题相关性读取；awrap_model_call 临时注入 HumanMessage，既不成为系统指令，也不写入 checkpoint。服务端当前时间另行作为可信上下文提供。记忆只存枚举值、更新时间、source_request_id / source_thread_id；回执与修改同事务，防止 checkpoint 重放复活已删除的偏好。MEMORY_ENABLED=false 关闭自动提取与注入。

## DeerFlow Reference

阅读 `agents/middlewares/memory_middleware.py`、`agents/middlewares/dynamic_context_middleware.py`、`agents/memory/manager.py`，保留显式用户归属、独立 Store / Service 和用户数据不提升为 SystemMessage 的原则。独立实现小型偏好库，不复制完整记忆 backend、定时任务或长期事实抽取系统。

## Tests

阶段初轮完整测试 **90 passed / 1 skipped**，19.14 秒。Memory 覆盖跨 thread / 重启、来源标识、健康事实 / 引用 / 否定排除、纠正与删除、跨用户隔离、请求重放不复活记忆及关闭功能。后续补充 SDK 真正的 tool-call / SSE 协议、PDF 与无进展保护，最终计数和时间以 [机器可读验收记录](phase-2-6-validation.json) 为准。

真实回环 HTTP smoke 已验证 healthz、OpenAPI、chat、trace header、会话历史、记忆提取与删除、文档索引和 TCP SSE。首次在 Windows 临时 SQLite 清理阶段失败，已改为测试进程文件信号触发 Uvicorn 优雅关闭，并在报告成功前检查端口关闭与临时目录清理。复验通过。没有保留测试服务。

## Known Issues

- 未执行真实 provider / 神经 embedding 在线联调或医学质量评测；fake 和 MockTransport 结果不是生产模型效果。
- 偏好提取采用明确句式和枚举，尚非开放式 LLM extraction；并发不同会话修改同一偏好时最后完成事务的值生效。
- SQLite + 会话 admission 仅支持单 worker；大型向量索引、事件重放、完整重试策略、用户认证系统、schema migration 和生产部署加固尚属后续扩展。
- 文档指令和 Memory 均按不可信数据传给模型，实际模型抵抗 prompt injection 的能力仍需后续评测。
- 当前没有 Web 前端或 SubAgent，分别属于 Phase 9 和 Phase 7。

## Next Phase

按用户本次要求停在 Phase 6 结束。下一开发阶段为 Phase 7 Multi-Agent，本次未提前创建子 Agent 运行系统或前端。
