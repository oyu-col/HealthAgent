# persistence：应用数据与事务边界

- 对应目录：`backend/app/persistence/`
- 核对日期：2026-10-04
- 源码：[目录](../../../../backend/app/persistence/)；上级：[app 说明](../README.md)

## 本层管理什么

该目录把业务数据库访问从工具和模型逻辑中分离，所有应用数据保存在 health.db。LangGraph 的 checkpoints.db 由应用 lifespan 另行管理，不在这里自建 checkpoint 表。

| 文件 | 当前责任 |
| --- | --- |
| [database.py](database.py.md) | 异步 SQLite engine/session 生命周期及 PRAGMA |
| [models.py](models.py.md) | 健康、文档、会话、写回执和偏好 ORM 模型 |
| [health_repository.py](health_repository.py.md) | 健康记录写入去重、owner 查询 |
| [knowledge_repository.py](knowledge_repository.py.md) | 文档元信息和完整索引发布、检索候选 SQL |
| [memory_repository.py](memory_repository.py.md) | 偏好 upsert/删除与请求回执 |
| [thread_repository.py](thread_repository.py.md) | 会话 owner、活动请求和完成回执 |
| [trace_repository.py](trace_repository.py.md) | 单独 TraceBase/TraceRecord、有限保留与隔离查询 |
| [__init__.py](__init__.py.md) | 包标记说明 |

## 应理解的事务边界

健康记录与 WriteReceipt 同次提交，防止业务行已插入而去重回执丢失。偏好与 MemoryReceipt 同次提交，防止恢复旧请求复活已删除偏好。文档 begin 与 finish 分两次提交，允许展示失败状态；finish 把片段替换和最终状态原子发布。Thread 回执独立于 checkpoint，Trace 又独立于健康写入，不能把整个 Agent 执行解释成一笔全局事务。

查询在 SQL 中加入可信 user_id；公共检索则按 visibility 和 owner 联合约束。普通结果通过 public_row 去掉 user_id，但“结果里没有 user_id”不等于授权，真正授权在查询条件。

## 限制与维护

SQLite 使用 WAL、外键检查、5 秒 busy_timeout，当前单 worker。create_all 只创建缺失的表，不会自动升级已有字段/约束。当前没有通用迁移框架、完整审计归档、加密存储或后台垃圾回收；Trace 有数量保留策略，其他业务表并无自动容量裁剪。增加字段应设计迁移并检查回执旧 JSON、索引版本和隐私边界。
