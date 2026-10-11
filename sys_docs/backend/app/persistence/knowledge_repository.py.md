# knowledge_repository.py：文档和索引的原子发布

- 对应源码：`backend/app/persistence/knowledge_repository.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/knowledge_repository.py) · [目录说明](README.md)

## 职责

将文档元信息、索引标识与文本向量片段持久化，并在 SQL 阶段完成私人/公共可见性过滤。本模块不解析文件、不生成向量、不执行余弦排序。

metadata() 合并 HealthDocument 的 public_row 与 visibility、source、index_version、error_code，作为导入/列表统一结果。公开文档信息不含 user_id。

## begin() 与 finish()

begin() 按 user_id+visibility+content_hash+index_version 查重复索引；命中返回已有文档元数据。否则创建 HealthDocument（类型由扩展名小写推导，初始 pending），flush 得到 id，再创建 DocumentIndex，两行同事务 commit。

finish() 按 document_id+user_id 取文档、按 id 取对应索引；更新 parse_status/index_status/error_code，删除该文档旧 KnowledgeChunk，若有新 chunks 则批量添加，最后统一 commit。默认状态为 parsed/indexed。失败调用也会清空片段，保证失败文档不以残留部分索引参与查询。

begin 与 finish 不是同一事务：解析/外部 embedding 期间文档可以保持 pending，失败后仍有可见状态。Service 的导入锁负责支持部署下的串行化；begin 未实现跨进程唯一冲突重试。

## candidates() 的授权先于排序

- scope=public：仅 visibility=public。
- scope=personal：visibility=personal 且 owner=user_id。
- scope=both：上述两类取并集。
- 所有模式都要求当前 index_version 且 HealthDocument.index_status=indexed。

查询联结 KnowledgeChunk、DocumentIndex、HealthDocument，最多取 5001 条。第 5001 条是容量探针，[检索器](../rag/retriever.py.md) 超过 5000 则失败，不在未经授权数据上排序后再过滤。返回 ORM 元组仅供内部计算，不直接作为 HTTP JSON。

list(user_id) 只列该 owner 的文档，按 created_at 倒序取 100 条；它不是公共知识库目录，暂无分页游标。

## 限制与修改注意

finish 假设调用的是 begin 后仍存在的合法文档，查不到对象时没有自定义 not_found 分支；外部删除 API 未来增加时需重新处理并发缺失情形。source 是出处字符串，不会自动打开或抓取 URL。当前没有原始文件存储、索引迁移或历史版本清理任务。

[集成测试](../../tests/integration/test_rag.py.md) 覆盖失败索引不可查、重传同 id、重启后出处保留、私人/公共分域和无效文件。修改 owner、版本或 indexed 过滤条件是安全敏感变更，应保留这些断言。
