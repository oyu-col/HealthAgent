# Phase 2 — Tool Runtime

## Completed

已完成五类健康数据模型、SQLite 存储、参数校验、统一 ToolResult、Service / Repository 分层和八个健康工具。`search_health_knowledge` 在 Phase 5 接入实际检索后注册。模型通过框架工具节点获得 observation 再回答。服务端支持本机固定用户及 bearer token 到用户的映射。

## Files Changed

后端新增 `app/domain/`、`app/persistence/`、`app/services/health.py`、`app/tools/health.py`、`app/auth.py`、工具边界 middleware；更新配置、lifespan、Lead Agent、模型适配与测试。依赖锁定 SQLAlchemy 2.1.3、aiosqlite 0.22.1。

## Design

Tool → Service → Repository → SQLAlchemy / SQLite。用户身份由隐藏的 ToolRuntime context 注入，所有查询限定 owner。输入时间必须带时区，数据库统一 UTC。单位匹配指标类型，未知营养值不猜测。写入与幂等回执同一事务提交；同请求的相同业务参数只保存一次，相同操作标识改参数报冲突。数据库异常不会盲目重放写操作。工具参数错误转为固定格式 observation，框架中断与取消保留。启用框架工具调用上限和既有步骤、超时预算。

## DeerFlow Reference

阅读 `tools/builtins/clarification_tool.py`、`agents/middlewares/tool_error_handling_middleware.py` 的 schema 和框架工具包装方式。保留控制流信号与错误边界设计，独立实现健康工具；不复制技能、沙箱或远端工具基础设施，也不把含敏感参数的原始异常写日志。框架接口核对了 [LangChain runtime](https://docs.langchain.com/oss/python/langchain/runtime)。

## Tests

2026-10-03：首轮完整测试 75 passed / 1 skipped（真实 provider 需显式开启）。真实 create_agent 图完成工具写入、数据库验证、ToolMessage observation 和最终回答；测试覆盖校验、时区、token 身份、跨用户隔离与重复写入。后续补充并发幂等、饮食、运动、趋势测试，结果见最终阶段验收记录。

## Known Issues

fake 是链路演示，不具备自然语言工具规划能力；工具闭环使用确定性测试模型验证，不能代表真实模型效果。本机 local 模式固定一个用户，仅适合回环地址；共享访问必须配置 token。没有记录删除 / 覆盖接口。SQLite 首版使用 create_all 创建新表，已有表字段迁移尚未引入迁移框架。

## Next Phase

Phase 3：持久化 Thread、官方 checkpointer、继续会话和失败恢复。
