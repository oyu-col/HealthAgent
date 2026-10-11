# integration：真实框架与本地存储的集成边界

- 对应目录：`backend/tests/integration/`
- 核对日期：2026-10-11
- 实际目录：[integration](../../../../backend/tests/integration)

本目录通过可注入模型、临时数据库、ASGI/流及 SDK MockTransport 验证多个层次协同。测试不是只检查函数存在，也不依赖真实医疗信息。

| 测试文件 | 核心边界 |
| --- | --- |
| [test_api.py](test_api.py.md) | 应用请求、校验、标识与安全错误 |
| [test_health_tools.py](test_health_tools.py.md) | 工具→业务→SQLite 写查、单位、owner 和幂等 |
| [test_threads.py](test_threads.py.md) | 持久历史、重启、请求冲突、并发与 checkpoint 恢复 |
| [test_streaming.py](test_streaming.py.md) | 原生流→SSE、UTF-8 分片、工具事件、失败和取消 |
| [test_provider_transport.py](test_provider_transport.py.md) | 真实 SDK 的离线 Chat Completions/tool calling/stream 协议 |
| [test_rag.py](test_rag.py.md) | 解析、索引原子发布、去重、证据引用与私人/公共隔离 |
| [test_memory.py](test_memory.py.md) | 提取、注入、持久化、删除及回放防复活 |
| [test_subagents.py](test_subagents.py.md) | 三角色权限、隔离、共享预算与并发回收 |
| [test_reliability.py](test_reliability.py.md) | 瞬态读取重试、写入未知结果、超时与守卫 |
| [test_observability.py](test_observability.py.md) | Trace 持久化、真实回调、取消和数据最小化 |
| [test_replay_integrity.py](test_replay_integrity.py.md) | Trace 故障下已完成回执不可变、并发保留容量 |
| [test_ui_api.py](test_ui_api.py.md) | 工作台依赖的可信身份、记录接口、状态和静态资源 |
| [test_benchmark_runner.py](test_benchmark_runner.py.md) | 真实评测执行、oracle 与决策隔离、幂等重放、SQL 引用核验及临时数据库回收 |

阅读时将测试操作与最后断言一起看：返回 success 不能替代真实数据库记录检查；SSE HTTP 200 不能替代 completed；Trace completed 也不能替代业务正确性。集成测试用确定性模型控制分支，真实 provider 质量仍需另行评测。

Phase 11–12 的 Benchmark Runner 集成测试将案例结构和判分规则放回实际应用链路，尤其通过只修改 expected oracle 观察“实际执行不变但评分失败”，防止评测用标准答案填造数据库或模型响应。完整目录设计见[Benchmark 说明](../../../benchmark/README.md)。
