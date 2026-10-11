# Phase 1 交付记录

日期：2026-10-03。阶段：HealthAgent Skeleton。状态：**已完成本地骨架验收；真实 provider 联调未执行。**

## Completed

- 独立 Python 包 health-agent、虚拟环境、pyproject 和 uv.lock。
- FastAPI app factory / lifespan、healthz、非流式 chat、统一错误 DTO、服务端 trace / run 标识。
- 真正的 LangChain create_agent / LangGraph 图，标准消息 state、公开 context 参数、显式 `ainvoke(version="v1")` 字典结果。
- 明确标记的本地 fake 模式，以及可配置的 ChatOpenAI provider；没有隐式凭据继承或失败后自动 fake 降级。
- 输入长度校验、总超时、provider timeout / 有限 SDK 重试、图步数预算、取消传播和输出内容块过滤。
- 脱敏 run 结果 / 耗时日志，禁用继承环境变量的外部追踪。
- 66 项离线测试通过；真实本地 Uvicorn HTTP smoke 通过；真实模型测试默认 skip。

## Files Changed

路径均相对 HealthAgent 根目录。

| 文件 / 目录 | 内容 |
| --- | --- |
| `.env.example` | fake / provider 样例，无真实密钥 |
| `.gitignore` | 测试临时目录、构建产物排除 |
| `backend/pyproject.toml`、`uv.lock`、`.python-version` | 独立工程、依赖锁定、Python 3.12、pytest / Ruff |
| `backend/AGENTS.md` | 后端开发、测试和隐私约定 |
| `backend/app/config.py` | 根目录 .env、Settings、启动校验 |
| `backend/app/main.py`、`dependencies.py` | 生命周期、依赖注入、HTTP 错误边界 |
| `backend/app/api/chat.py`、`schemas.py` | healthz / chat 与 DTO |
| `backend/app/models/demo.py`、`factory.py` | 演示模型、provider 客户端及资源关闭 |
| `backend/app/agents/lead_agent.py`、`prompts.py` | create_agent 装配、健康辅助规则 |
| `backend/app/agent/context.py`、`runtime.py`、`errors.py` | 可信上下文、invoke、结果、预算与错误 |
| 源码目录内 `__init__.py` | 独立 Python 包 |
| `backend/logging.json` | 基础运行日志；关闭 HTTP access log |
| `backend/tests/conftest.py`、`fakes.py` | 环境隔离、禁止真实 HTTP transport、可观察测试模型 |
| `backend/tests/unit/` | 配置、runtime、模型 factory / 清理 |
| `backend/tests/integration/` | ASGI、隔离、真实 ChatOpenAI SDK 的离线协议 |
| `backend/tests/live/test_provider.py` | 显式 `--run-live` 的 provider smoke |
| `backend/scripts/smoke.py` | 启动、访问并关闭真实本地 Uvicorn 服务 |
| `README.md`、`AGENTS.md`、`docs/architecture.md`、`docs/phase-1-plan.md` | 当前阶段、启动步骤和后续边界 |
| 本文件、[phase-1-validation.json](phase-1-validation.json) | 阶段交付与已执行验证摘要 |

`.venv`、测试缓存 / 临时文件是已忽略的生成物。未创建真实模型 `.env`，没有修改原始规范副本或 DeerFlow 源码。

## Design

### 一个框架链路，两种模型

fake 和 provider 都经过同一 factory / runtime 进入 create_agent 图。fake 明示演示；provider 使用 Chat Completions，URL / model / key 由服务端配置。客户端只能发送 message，不能控制用户、工具、模型或 RunnableConfig。

RunContext 是冻结的数据类，携带固定开发身份、时区、trace_id 和 run_id。无 checkpointer 时，每次调用传入新的 HumanMessage；不保留上一轮历史，不在并发请求间共享消息列表。四请求测试验证各自回答与标识。

### 生命周期与错误

lifespan 创建模型和图；factory 创建的两个 HTTP 客户端由上下文管理器关闭，构造失败也释放。测试注入的模型由调用者拥有。模块导入不会联网。

总 timeout 限制完整 invoke；provider 自带 timeout / max_retries，没有应用层重复模型重试循环。预算耗尽、服务错误、无完整文本有不同错误码。CancelledError 继续传播，不转成成功答案。当前无工具，工具重试 / re-plan / max_tool_calls / 重复无效调用检测在后续阶段实现。

只返回最后 AIMessage 的可见文本，忽略 reasoning / image 等内容块；拒绝工具调用未完成、空文本及已知截断结果，不返回完整 state。

### 配置与观测

固定读取项目根 .env，要求显式 mode；provider 缺必要字段即报错。基础日志仅记录标识、结果码和耗时；错误不回显输入或原始异常。runtime 使用 LangSmith tracing context 禁用外部自动追踪，并验证在外部环境变量开启 tracing 时仍关闭。

额外的 logging.json 让真实 Uvicorn 启动也输出基础运行日志，smoke.py 提供可复现 HTTP 启动验证。没有借此扩展到业务工具、存储、UI 或完整 Trace。

## DeerFlow Reference

本阶段重新读取以下源码并独立实现：

| 参考 | 学习与简化 |
| --- | --- |
| [lead_agent/agent.py](../../deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)，L1274 | 配置模型、工具与 prompt 后 create_agent；本项目只保留空工具集、健康规则和 RunContext |
| [models/factory.py](../../deer-flow/backend/packages/harness/deerflow/models/factory.py)，L364 | 模型 factory；仅一个 provider adapter + demo，不移植 provider patch |
| [gateway/app.py](../../deer-flow/backend/app/gateway/app.py)，L396 | FastAPI lifespan；移除扩展、数据库和多后台服务 |
| [runtime/runs/worker.py](../../deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py) | 图执行与 HTTP 分层；当前 ainvoke，无 bridge、私有 runtime 注入和后台 RunManager |

公开接口对照 [Agents](https://docs.langchain.com/oss/python/langchain/agents)、[Streaming / invoke 格式](https://docs.langchain.com/oss/python/langgraph/streaming) 与 [ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai) 官方文档。实际兼容性以锁定依赖和真实框架测试为准。

## Tests

Windows / Python 3.12.10。主要锁定版本：LangChain 1.4.3、langchain-core 1.6.6、LangGraph 1.2.12、langchain-openai 1.6.7、FastAPI 0.142.2、Pydantic 2.13.5、OpenAI SDK 2.54.0、Uvicorn 0.54.0。完整清单见 backend/uv.lock，未照搬 DeerFlow lockfile。

| 实际执行 | 结果 |
| --- | --- |
| `uv sync --group dev --python <本机 Python312 路径>` | 创建独立 .venv 并成功安装 editable health-agent 与依赖 |
| `uv sync --group dev --link-mode copy` | 更新 tracing 控制的显式依赖并锁定成功 |
| `uv sync --locked --offline --group dev --link-mode copy` | 最终锁定依赖离线安装校验通过 |
| `.venv/Scripts/python.exe -m pytest -q` | **66 passed, 1 skipped，10.84 秒** |
| `.venv/Scripts/ruff.exe check .` | 通过 |
| `.venv/Scripts/ruff.exe format --check .` | 通过，源码已格式化 |
| `.venv/Scripts/python.exe scripts/smoke.py` | healthz / OpenAPI / chat / trace header 全部通过；fake 模式、loopback 端口 50536，子进程已关闭 |
| 文档与独立性检查 | 80 个本地链接有效；57 个 DeerFlow 参考文件哈希未改变；规范副本一致；无 DeerFlow import / 依赖 |

包括真实 create_agent 图与 context、并发 / 连续请求隔离、超时 / 取消、循环测试图触发预算、错误分类与脱敏、输出过滤、配置缺失、非法身份字段拒绝、客户端关闭、实际 provider SDK 的 MockTransport 请求解析、外部追踪关闭。

首轮为 63 passed / 1 skipped / 1 error，错误来自 Windows 系统 pytest 临时目录不可访问。改为项目内 .pytest-tmp 后消除问题，加入两项补充测试后得到上表结果。初始 Ruff 格式问题已修复。运行 Python 需要启动工作区外的解释器，相关测试与启动命令经授权执行；未修改系统权限或删除系统临时目录。

**未执行**：真实 provider 调用、医学质量评测、Domain Benchmark、前端测试，以及尚未实现的 Tool / DB / checkpoint / RAG 测试。离线 pass 不代表模型效果或性能提升。

## Known Issues

- 未提供 HealthAgent 真实模型配置，在线 provider 联调未验证；live smoke 缺配置会 skip，不能视为通过。
- 当前是单用户本地骨架，没有多用户鉴权或健康数据存储。固定 local-user 不是认证机制。
- 健康边界主要由 system prompt 表达，完整 guardrail 尚未实现 / 评测；fake 不证明模型遵循医学规则。
- 每个 POST 为独立单轮调用，无持久会话、SSE 或 Web UI。
- 仅离线验证标准 Chat Completions，第三方服务扩展能力未验证。
- 本地无 Git 元数据，无法提供 commit / diff；没有初始化或提交 Git 仓库。

## Next Phase

Phase 2 — Tool Runtime：明确 schema、统一 ToolResult、显式注册与 middleware 执行边界，接入 Health Service / Repository / SQLite。先用写入与查询验证真实数据库闭环，再补齐规范健康工具；用户隔离、单位 / 时间校验与写入幂等从首个工具开始验证。
