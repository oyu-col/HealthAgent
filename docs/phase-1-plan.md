# Phase 1 — HealthAgent Skeleton 实现计划

状态：**Phase 1 已按此计划完成。** 本文保留实施前的计划与验收标准；实际文件、版本、命令和结果以 [Phase 1 交付记录](phase-1-delivery.md) 为准。真实 provider 尚未联网验证。

## 1. 完成定义与范围

目标是一个可独立安装、可通过 FastAPI 调用的最小 LangChain / LangGraph Lead Agent，跑通 User → Agent → Answer。优先验证真实框架的装配、调用和错误处理，不能仅创建空目录和返回固定 HTTP 文本就声称 Agent 跑通。

本阶段包含：Python 工程、配置校验、模型 factory、create_agent、非流式聊天 API、基础运行限制、可替换模型的离线测试、README 启动说明。不提前实现健康数据库、九个业务工具、持久 Thread、SSE、RAG、Memory、SubAgent 或完整 Web；这些仍按规范所属阶段推进。

## 2. 依赖与工程初始化

选择 Python ≥ 3.12 和 uv。创建独立 `backend/pyproject.toml`、虚拟环境与 lockfile，不引用 `../deer-flow`，不复制它的 uv workspace / override-dependencies。

| 类别 | 第一阶段依赖用途 |
| --- | --- |
| FastAPI + uvicorn | HTTP 应用与本地运行 |
| Pydantic + pydantic-settings | 请求、响应和环境配置 |
| LangChain + LangGraph + langchain-core | `create_agent`、消息、模型接口、图运行与限制 |
| langchain-openai | 第一种可配置 provider adapter；可连接明确支持的兼容服务 |
| pytest + pytest-asyncio + httpx | 离线单元 / 集成测试 |
| Ruff | 格式及静态检查 |

以上是拟采用依赖，不是已安装结果。实施时先核对当时官方 API、解算并锁定一组兼容版本；用 import / 最小图测试验证。DeerFlow lockfile 可作参考，不能原样继承它全部依赖。SQLite saver、SQLAlchemy、向量库、embedding、Next.js 等到相应阶段引入。

不硬编码具体模型名称，provider 的 base_url、model、key 由环境变量配置。基于兼容 API 的服务可能不支持工具 / 流功能，Phase 2 / 4 分别增加能力验证。

## 3. 拟新增文件和职责

| 文件（相对项目根） | 具体责任 |
| --- | --- |
| `.env.example` | 无密钥样例、fake / provider 模式说明、运行限制 |
| `backend/pyproject.toml`、`backend/uv.lock` | 独立包、依赖与测试 / lint 配置 |
| `backend/app/__init__.py` | 包入口，不在 import 时联网 |
| `backend/app/main.py` | `create_app`、lifespan、路由及错误处理 |
| `backend/app/config.py` | Settings，读取项目根配置文件的明确路径 |
| `backend/app/dependencies.py` | 测试可覆盖的配置 / model / runtime 依赖 |
| `backend/app/models/factory.py` | 创建 BaseChatModel，配置 provider timeout / retry |
| `backend/app/agent/context.py` | 服务端 RunContext；trace_id、run_id、固定开发用户、timezone |
| `backend/app/agent/runtime.py` | 异步调用、超时、step 预算、最终消息提取 |
| `backend/app/agent/errors.py` | 分类 provider / timeout / graph / invalid output 错误 |
| `backend/app/agents/lead_agent.py` | `create_agent(model, tools=[], system_prompt, context_schema)` |
| `backend/app/agents/prompts.py` | 健康信息辅助定位、数据不足和医疗风险基础规则 |
| `backend/app/api/chat.py`、`schemas.py` | 请求校验与响应 DTO，禁止任意 framework config 注入 |
| `backend/tests/conftest.py`、`fakes.py` | 可注入 BaseChatModel 测试实现；保留真实图执行 |
| `backend/tests/unit/` | 配置、runtime 错误、消息转换测试 |
| `backend/tests/integration/` | ASGI → runtime → 真实 create_agent 图 → fake model |
| `backend/tests/live/` | 显式开启的 provider smoke，默认跳过 |
| `README.md`、`docs/phase-1-delivery.md` | 实际启动步骤、测试结果、限制与下一阶段 |

Phase 1 不建立无字段的自定义 AgentState；直接使用标准状态。当 Phase 2 确实需要 run 计数或证据字段时，再加入 `agent/state.py`。

## 4. 配置契约

拟用统一 `HEALTH_AGENT_` 前缀：

| 配置 | 规则 |
| --- | --- |
| `MODEL_MODE` | 显式 `fake` 或 `provider`；fake 响应必须标记，禁止 provider 失败自动降级 fake |
| `MODEL_NAME` / `MODEL_BASE_URL` / `MODEL_API_KEY` | provider 模式校验必要字段，密钥使用 SecretStr 且不进响应 / 日志 |
| `REQUEST_TIMEOUT_SECONDS` | 正有限值，包围完整 invoke |
| `MODEL_TIMEOUT_SECONDS` / `MODEL_MAX_RETRIES` | 有界 provider 调用，不能比总预算无限扩大 |
| `MAX_STEPS` | 正整数，服务端转为 recursion_limit；不由客户端任意指定 |
| `MAX_INPUT_CHARS` | 限制输入大小；校验空白字符串 |
| `LOCAL_USER_ID` / `TIMEZONE` | 开发身份固定在服务端；验证时区 |

测试 fixture 使用显式 Settings 实例，避免测试读取真实 `.env` 或开发者密钥。应用 import 不创建外部连接。lifespan 构建可复用模型和 agent，运行数据不写进全局可变用户状态。

## 5. HTTP 和 Runtime 契约

`GET /healthz` 返回服务状态、model_mode、phase，不触发计费模型调用、不泄漏 key / base_url 凭据。该路由表示应用已启动，不声称 provider 当前可用。

`POST /api/chat` 请求只含 `message`，非空且有长度上限。Phase 1 每次请求为独立单轮调用，不接收 thread_id、user_id、tool 列表、模型自定义 URL 或任意 RunnableConfig。多轮和持久化在 Phase 3 加入。

成功响应包含 `answer`、`trace_id`、`run_id`、`model_mode`、`termination_reason`。消息内容可能是字符串或内容块，runtime 只提取最后可见 AI 文本；没有可展示结果时返回明确错误，不把 Python repr 或完整 state 当作答案。

错误统一为 `{error: {code, message, trace_id}}`，错误信息不包含 provider 原始请求、密钥或用户健康原文。拟定语义：非法请求 422；总超时 504；provider 暂时不可用 503；调用 / 协议失败 502；图执行预算耗尽返回受控错误与 `step_limit`，不伪装正常完成。

最小内部调用链：

```text
FastAPI schema validation
  → trusted RunContext（request / run / trace 标识）
  → HealthAgentRuntime.ainvoke
  → asyncio.timeout + recursion_limit
  → create_agent 返回的 LangGraph 图
  → BaseChatModel
  → final visible AI message
  → ChatResponse
```

选定 `ainvoke` 返回格式并固定解析契约；如果采用显式 `version="v2"`，按 GraphOutput.value 读取，不与旧 dict 路径混用。以实际锁定版本测试结果为准。框架 context 使用公开 `context=`；不复制 DeerFlow 对私有 config key 的 runtime 注入。

## 6. 实施顺序

1. 重读规范、README、Phase 0 结论；检查本地 Git 状态和已有文件，防止覆盖后续工作。
2. 创建 Python 工程并锁定依赖；验证导入与版本，记录实际命令和结果。
3. 先写 Settings 校验和 fake model fixture；测试 fake 必须实现框架所需接口，并可记录收到的消息。
4. 创建 lead factory；测试它执行真实图并调用注入模型，固定 system prompt 和独立输入。
5. 完成 runtime timeout / step budget / response extraction；测试异常和取消清理。
6. 接 FastAPI healthz / chat、DTO 和依赖覆盖；跑 ASGI 集成与 OpenAPI schema 检查。
7. 若已经提供可用 provider 配置，执行一次明确的真实模型 smoke；未配置则跳过并记录原因，不搜集或读取 DeerFlow 的密钥。
8. 更新 README 和阶段交付记录，记录测试结果与已知问题，下一阶段为 Tool Runtime。

## 7. 必须执行的验收

| 场景 | 验收方式 |
| --- | --- |
| 独立安装 | 在 HealthAgent 自己的环境解析依赖；不存在 `deerflow` imports / path 依赖 |
| 合法配置 / 缺 key / 非法预算 | Settings 单元测试；provider 配置错误不静默变 fake |
| 最小 Agent 图 | spy fake 模型收到 HumanMessage 与健康规则；返回结果经过图 / runtime |
| HTTP 成功与校验失败 | ASGI 测试验证 DTO、status、空输入、超长输入和意外字段 |
| 并发请求隔离 | 两个独立请求的 messages / IDs 不相互污染 |
| provider 错误与 timeout | fake 故障注入验证错误码、预算和资源清理 |
| 图预算耗尽 | 可控异常 / 小测试图验证错误映射；不把无工具单轮假称循环检测测试 |
| 输出与日志 | 不包含测试 secret、完整内部 state、原始 provider 错误载荷 |
| 无凭据运行测试 | 默认测试不联网；live marker 需显式开启 |
| 手动启动 | loopback 启动后检查 healthz、OpenAPI 和一次 chat；注明 fake / provider 模式 |

以下保留计划命令；实际执行记录见交付文档，日常启动和测试使用更新后的 README：

```powershell
Set-Location D:\AgentFiles\HealthAgent\backend
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -m "not live"
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

实现时应确保 `.env.example` 与 root 配置加载路径、测试 marker 和上述命令完全一致。真实模型 smoke 需在 README 列出准确命令；没有执行就不能列为通过。

## 8. 完成后仍不具备的能力

Phase 1 只证明工程和 Agent 调用链可运行，不证明健康回答质量、RAG groundedness 或模型工具选择准确率。领域数据、工具、会话恢复、流式 UI 与 Benchmark 均以后续阶段验收为准。模型供应商未配置不阻止离线骨架验收，但交付必须明确真实 provider 联调尚未验证。
