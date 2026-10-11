# services：业务流程编排

- 对应目录：`backend/app/services/`
- 核对日期：2026-10-04
- 源码：[目录](../../../../backend/app/services/)；上级：[app 说明](../README.md)

## 作用与分层目的

Service 是 HTTP 接口和 Agent 工具共享的业务入口。接口负责身份与协议，工具负责模型可调用的参数包装，Service 负责数据校验、时间转换、状态流程、业务错误和读取策略，Repository 负责 SQL 与提交。

| 文件 | 当前责任 |
| --- | --- |
| [health.py](health.py.md) | 健康写入、列表、描述性趋势 |
| [knowledge.py](knowledge.py.md) | 文档导入、解析/向量流程、范围检索 |
| [memory.py](memory.py.md) | 明确偏好提取、修改、相关性筛选 |
| [threads.py](threads.py.md) | 会话所有权、单 worker 执行准入、恢复和回执 |
| [__init__.py](__init__.py.md) | 包说明 |

## 数据边界与事务

各服务的 user_id 由 API 已认证身份或 RunContext 提供，不是模型 record 字段。HealthRepository 将记录与写回执同事务提交；MemoryRepository 将偏好和请求回执同事务提交；知识导入先创建 pending 元数据，再用另一事务发布完整索引；Thread 回执与 LangGraph checkpoint 是两个独立存储边界。Service 之间没有跨整个对话的大事务，后续模型或 Trace 失败不能撤销已经提交的健康事实。

## 错误与部署限制

健康/检索工具使用 ToolResult 表达可观察业务失败；会话/管理 API 的流程错误使用 AgentError。取消不应转换成成功，未知存储异常交给上层安全映射。threads 的 admission、knowledge 的 ingest_lock 都是进程内锁，当前部署只支持单 worker。扩展为多进程不能仅改变启动参数，需要重新设计准入与幂等并发控制。

学习建议：先读 health，再看对应 Repository；理解记录事务后读 threads 的“业务回执与 checkpoint 分离”，最后读 knowledge 和 memory 的不同持久化语义。
