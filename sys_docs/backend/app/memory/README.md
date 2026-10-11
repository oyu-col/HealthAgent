# memory：明确偏好提取与临时上下文

- 对应目录：`backend/app/memory/`
- 核对日期：2026-10-04
- 源码：[目录](../../../../backend/app/memory/)；上级：[app 说明](../README.md)

## 设计目的

Memory 只表达用户明确同意保存的稳定偏好，帮助跨会话调整回答。体重、病史、饮食记录等重要事实进入结构化健康数据库；文档片段进入 RAG，两者都不由自由文本 Memory 替代。

- [extraction.py](extraction.py.md)：有限 key/value allowlist 和严格中文表达式。
- [middleware.py](middleware.py.md)：Agent 前提取、模型调用前临时注入、服务端时间上下文。
- [__init__.py](__init__.py.md)：包说明。

## 流程与权限

当前请求的 HumanMessage.id 对应可信 context.operation_id → extraction → MemoryService → MemoryRepository 同事务保存偏好和回执。模型调用时根据当前问题选择偏好，新增名为 healthagent_preferences 的临时 HumanMessage；不作为 SystemMessage，不回写 checkpoint 历史。日期/时区则由可信服务端时间追加到系统上下文，和用户偏好数据分开。

偏好 API 可查看、更正、忘记。MEMORY_ENABLED=false 关闭 Agent 自动提取/注入，不删除已有偏好，也不关闭管理 API。自动保存发生在模型调用之前，之后模型失败并不意味着偏好未保存。

## 限制与验证

只有语言、回答风格、饮食偏好、运动偏好四类；关键词相关性与严格语法故意保守，不支持任意自然语言记忆、向量记忆或自动健康摘要。[Memory 集成测试](../../tests/integration/test_memory.py.md) 验证跨会话持久化、引用不当授权、隔离、纠正/忘记和回放不复活。
