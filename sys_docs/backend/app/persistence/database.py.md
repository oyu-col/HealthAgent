# database.py：业务数据库资源生命周期

- 对应源码：`backend/app/persistence/database.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/persistence/database.py) · [目录说明](README.md)

## 作用和执行过程

database_session(data_dir:Path) 是 asynccontextmanager，由 main.py lifespan 持有：

1. asyncio.to_thread 创建数据目录，避免目录操作占用事件循环。
2. 为 data_dir/health.db 建立 sqlite+aiosqlite 异步 engine。
3. 通过同步 engine 的 connect 事件为每个 SQLite 连接执行 PRAGMA foreign_keys=ON、busy_timeout=5000、journal_mode=WAL。
4. engine.begin 中运行 Base.metadata.create_all，创建 [models.py](models.py.md) 注册的业务表。
5. yield async_sessionmaker(engine,expire_on_commit=False) 给各 Repository。
6. 无论正常退出或异常，finally await engine.dispose() 释放连接。

expire_on_commit=False 允许 Repository 提交后读取已加载 ORM 属性并序列化，避免异步场景下隐式过期加载。它并不让 ORM 对象永久保持与数据库实时同步。

## 事务与权限

本模块只提供 session 工厂，不包住整个应用请求的事务；每个 Repository 自行 commit 或 session.begin。连接没有自动 owner 过滤，隔离必须由 Repository SQL 实现。health.db 含健康事实、原始聊天回执等私人内容，文件权限由部署环境保护，本模块没有加密或备份逻辑。

Trace 使用独立 TraceBase，因此 [TraceRepository.initialize()](trace_repository.py.md) 另外建表；LangGraph checkpoint 的数据库生命周期也不由该函数创建。

## 失败及修改注意

目录、连接和建表错误会传播并阻止正常启动，不自动切换到临时数据库，也不静默重建已有数据。create_all 并非迁移工具。WAL 与 busy_timeout 改善本机并发行为，但不能替代 Thread/Trace 的单 worker 准入锁。

健康、RAG、Memory、Trace 集成测试都通过真实临时 SQLite 使用本函数；[并发回执测试](../../tests/integration/test_ui_api.py.md) 与 [Trace 准入测试](../../tests/integration/test_replay_integrity.py.md) 验证上层并发事务行为。本次文档工作未重跑测试。
