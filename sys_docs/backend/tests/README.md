# tests：后端行为验证

- 对应目录：`backend/tests/`
- 核对日期：2026-10-04
- 实际目录：[tests](../../../backend/tests)

## 测试分工

| 入口 | 验证内容 |
| --- | --- |
| [unit/](unit/README.md) | Settings、模型工厂资源关闭、Runtime 边界及 Trace 回调计数 |
| [integration/](integration/README.md) | 真实框架图、临时 SQLite、HTTP API、SSE、恢复、owner 隔离和失败注入 |
| [live/](live/README.md) | 明确开启并配置凭据后的 provider 连通性检查 |
| [conftest.py](conftest.py.md) | 统一 fixture、环境变量隔离、默认禁外部 HTTP |
| [fakes.py](fakes.py.md) | 可观察模型和确定性工具选择模型 |
| [__init__.py](__init__.py.md) | 测试包标识，便于共享 fixtures/model imports |

## 怎样理解通过与跳过

多数测试替换模型决策，但仍运行真实 create_agent/LangGraph、Service/Repository 或 SDK。这样可以确定某次写入、幂等回放或取消确实发生，而不依赖非确定性的模型输出。MockTransport 验证 SDK 请求/解析协议，不能证明远程服务实际可用。

live 默认 skip，需要 --run-live；缺少配置也可能 skip。集成测试不是领域 Benchmark，历史 155 passed / 1 skipped 等数字见原阶段记录，本次文档任务没有重跑这些测试。

pytest 默认临时目录位于 backend/.pytest-tmp。测试数据是隔离的合成资料；不要为了方便把真实 data 目录或个人凭据接入默认测试。新增功能应覆盖其真实边界：写入应断言 DB，RAG 应断言 citation/owner，恢复应断言未重复提交，流应断言最终状态与取消回收。
