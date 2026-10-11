# models.py：业务 ORM 表结构

- 对应源码：`backend/app/persistence/models.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/models.py) · [目录说明](README.md)

## 基础约定

Base 为 SQLAlchemy DeclarativeBase。new_id() 生成 UUID 字符串；now() 获取当前 UTC 并去除 tzinfo，配合 SQLite DateTime 保存“无时区 UTC”。OwnedRecord 混入 id(UUID 主键)和 user_id(索引)，供健康/文档表使用。字段限制主要由 DomainModel 执行，ORM 的 String 长度本身不等于完整输入校验。

## 表与用途

| 类/表 | 关键字段与关系 |
| --- | --- |
| UserProfile / user_profiles | user_id 主键、age、height、created_at；已定义模型，当前服务并没有完整资料管理流程 |
| HealthMetric / health_metrics | 指标类型、数值、单位、measured_at；类型和时间有索引 |
| DietRecord / diet_records | 食物、数量文字、餐别、timestamp、可空 nutrition_info JSON |
| ExerciseRecord / exercise_records | 运动类型、分钟、公里、热量、timestamp |
| HealthDocument / health_documents | filename、document_type、created_at、parse_status/index_status（默认 pending） |
| WriteReceipt / write_receipts | user_id+operation_key 唯一约束、payload_hash、公开结果 JSON；保障健康写操作幂等 |
| ThreadRecord / threads | thread_id 主键、owner、创建时间、可空 active_request_id |
| ChatRun / chat_runs | user_id+request_id 联合主键、thread_id、原始 message、status、answer、run_id |
| DocumentIndex / document_indexes | document_id 外键兼主键，指向 HealthDocument；owner、visibility、content_hash、index_version、source、error_code |
| KnowledgeChunk / knowledge_chunks | document_id 外键指向 DocumentIndex；原文 text、page、start_index、embedding JSON |
| MemoryPreference / memory_preferences | user_id+key 联合主键，value、更新时间、source_request_id/source_thread_id |
| MemoryReceipt / memory_receipts | user_id+request_id 联合主键，防旧请求重复应用偏好 |

DocumentIndex 对 user_id、visibility、content_hash、index_version 设置组合唯一约束；文件名不在去重键内，所以相同用户同域同内容同版本但不同文件名也会复用已有文档。KnowledgeChunk 的外键未配置级联删除；当前没有公开文档删除功能，未来增加删除需按关联顺序处理。

## 数据与安全边界

ChatRun 明确保存原始请求和答案，因此不能将 health.db 宣称为仅脱敏元数据。Trace 独立模型在 [trace_repository.py](trace_repository.py.md)，不在本文件；checkpoint 状态位于另外数据库。各表 user_id 大多不是 UserProfile 外键：当前无需先插入完整个人档案才能存健康记录。

这些 ORM 模型不自动过滤 owner，也不实现 request 冲突判断。事务和查询限制分别位于 Repository，输入校验在 [domain](../domain/README.md)。不得仅依赖全局唯一 UUID 来替代 owner 授权。

## 变更注意和验证

已有部署通过 create_all 建表，没有自动列迁移。增加必填字段、改变 JSON 结构或唯一约束需考虑已有记录与幂等回执。健康时间需保持 UTC 约定。当前集成测试使用临时数据库覆盖记录、回执、索引、偏好和重启持久化；这不是生产数据迁移测试。
