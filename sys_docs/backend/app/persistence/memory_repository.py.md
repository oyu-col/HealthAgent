# memory_repository.py：偏好更新与防回放回执

- 对应源码：`backend/app/persistence/memory_repository.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/memory_repository.py) · [目录说明](README.md)

## 设计目的

MemoryRepository 存储当前有效偏好，记录最近来源，并确保同一个用户请求只应用一次。它不是聊天摘要仓库，不保存提取原句；合法 key/value 由 [MemoryService](../services/memory.py.md) 与提取器保证，Repository 本身不重复 allowlist 校验。

## list(user_id)

SQL 按 user_id 过滤并按 key 排序，输出 key、value、updated_at(Z)、source_request_id、source_thread_id。返回值不暴露 owner，也没有从别的用户继承默认偏好。

## apply(user_id,changes,request_id,thread_id)

先添加 MemoryReceipt(user_id,request_id) 并 flush。若联合主键冲突产生 IntegrityError，则 rollback 并返回 []，不再处理变化。对首次请求逐项应用：

- value=None：按 owner+key 删除当前偏好。
- 非空值：SQLite insert…on_conflict_do_update，以 user_id+key 为冲突目标，写 value、now() 和来源 request/thread。

回执与所有变化在一次 commit 中提交，返回输入 changes。只有回执成功并不够，后续偏好写入失败会使同事务回滚。

## 为什么重复请求不返回原变化

这里重复请求返回 []，而不是“再次执行原 upsert”。例如原对话记住 running，用户后来改成 swimming 或删除该偏好；旧 checkpoint 恢复时不得把 running 复活。这个策略与健康 WriteReceipt 返回原业务行不同，符合“偏好可纠正”的语义。

管理 API 每次创建新 request_id，因此可以继续覆盖同 key；自动对话提取沿用业务请求标识。来源只保存最后一次改变当前值的标识，不构成完整版本审计。

## 验证和边界

[Memory 集成测试](../../tests/integration/test_memory.py.md) 覆盖跨启动持久化、用户隔离、更正后删除、旧请求回放不复活。本模块没有偏好数量裁剪、回执清理或乐观版本检查；允许集合很小，但 MemoryReceipt 会随有效偏好请求增长。更改回执去重策略时必须保留上述纠正/忘记语义。
