# HealthAgent

基于 LangChain / LangGraph 独立实现的个人健康管理 Agent。DeerFlow 只作为源码与架构参考，运行不依赖 DeerFlow。

**当前工程交付范围：Phase 0–12。** 健康工具、SQLite、持久会话、SSE、RAG、Memory、三个专业 Agent、React 工作台和持久 Trace 已接入独立 Domain Benchmark；建立了基线、失败分析、修复和复跑闭环。当前真实模型连接受阻，在线能力验收尚未完成，不能用离线结果代替。实际结果见 [Phase 11](docs/phase-11-delivery.md)、[Phase 12](docs/phase-12-delivery.md) 与 [验收记录](docs/phase-11-12-validation.json)；历史 [Phase 7–10 验收](docs/phase-7-10-validation.json) 保留原样。

```text
API → 服务端身份 → Thread / Run → create_agent
                                  ├─ Health Tool → Service → Repository → health.db
                                  ├─ RAG Tool → Scoped Retriever → 文档片段 / 向量
                                  ├─ Memory Middleware → 显式偏好 / 临时上下文
                                  ├─ Delegate → Nutrition / Record / Research（只读）
                                  └─ LangGraph checkpointer → checkpoints.db
Graph callbacks / domain hooks → 脱敏执行元数据 → health.db / execution_traces
Graph messages / custom → SSE → React 工作台 / scripts/stream_client.py
```

`fake` 是带标识的本地回显模型，不理解自然语言工具请求；数据库、文档摄取、记忆和会话仍实际运行。健康工具闭环使用确定性测试模型及实际 ChatOpenAI SDK + MockTransport 验证。真实模型的规划、医学回答质量及在线 embedding 效果尚未验证，不能将离线测试当作领域 Benchmark。

## 启动

Windows / PowerShell，Python 3.12+、uv；本次验证使用 Python 3.12.10。

```powershell
Set-Location D:\AgentFiles\HealthAgent\backend
uv sync --locked --group dev
if (-not (Test-Path -LiteralPath ..\.env)) {
    Copy-Item -LiteralPath ..\.env.example -Destination ..\.env
}
uv run --no-sync uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --log-config logging.json
```

固定读取 HealthAgent 根目录 `.env`，同名 `HEALTH_AGENT_*` 环境变量优先。已有配置不会被覆盖。打开 [API 文档](http://127.0.0.1:8000/docs)；[healthz](http://127.0.0.1:8000/healthz) 返回 phase=12，不调用模型。按 Ctrl+C 停止自身服务器。

## Web 工作台

前端使用 React / TypeScript / Vite，参考 DeerFlow 的侧栏、居中对话、圆角输入框与资料面板，未复制 DeerFlow 主体或依赖其服务。Node.js 22.12+、pnpm 11；首次安装可能需要访问包仓库。

```powershell
Set-Location D:\AgentFiles\HealthAgent\frontend
pnpm install --frozen-lockfile
pnpm build
```

先完成构建，再按上方命令启动后端，打开 [HealthAgent 工作台](http://127.0.0.1:8000/)。FastAPI 同源提供首页和静态资源，浏览器 hash 路由支持刷新与历史返回。开发时另开终端运行 `pnpm dev`，访问 http://127.0.0.1:5173，`/api` 代理到本机 8000 端口；后端仍需运行。

- 健康对话：持久会话、增量输出、工具执行状态、停止与显式恢复，最终回答附执行记录入口。
- 健康记录：填写指标、饮食和运动，直接写入现有 Service / Repository；记录表单按请求 UUID 防重。
- 我的文档：上传 TXT / MD / PDF 或新建笔记，显示真实解析 / 索引状态，索引就绪后可发起文档提问。
- 长期偏好：按服务端允许值设置、更正、确认忘记；资料侧栏显示真实已存内容。

访问凭据只保存在当前页面内存；刷新需重新连接，更换凭据会取消请求并移除旧工作空间。没有持久化健康浏览器缓存。Markdown 不执行原始 HTML、不自动加载外部图片。移动端提供折叠导航，支持浅色 / 深色主题。

`fake` 模式页面会明确显示演示标识：表单、数据库、索引与会话真实工作，自然语言分析和自主委派需要配置 provider。UI 的静态参考和简化依据见 [DeerFlow UI 参考记录](docs/ui-deerflow-reference.md)。

默认 `AUTH_MODE=local` 是本机固定用户，只绑定回环地址。共享访问需配置 token 映射、HTTPS 和部署访问控制；请求中的 user_id / X-User-ID 不能改变身份：

```dotenv
HEALTH_AGENT_AUTH_MODE=token
HEALTH_AGENT_API_TOKENS={"alice":"replace-with-random-alice-token","bob":"replace-with-random-bob-token"}
```

使用独立随机凭据（至少 16 字符），客户端发送 `Authorization: Bearer <token>`。不要把密钥提交仓库。

## 对话、会话和恢复

```powershell
$payload = @{ message = '请记住：我喜欢简短的回答。' } | ConvertTo-Json
$result = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$result
```

`POST /api/chat` 接受 `message`、可选 UUID `thread_id` / `request_id`。不传 thread_id 创建新会话；下一轮传返回的 thread_id 继续历史。需要请求重试时，首次即提供 request_id 并重复使用；相同标识改内容返回 409。响应包括 answer、thread_id、request_id、run_id、trace_id、model_mode、memory_updates。X-Trace-ID 为服务端生成值。

| 接口 | 用途 |
| --- | --- |
| `POST /api/threads` | 创建空会话 |
| `GET /api/threads` | 当前用户最近 100 个会话 |
| `GET /api/threads/{thread_id}` | 可见对话与 pending 状态，不暴露内部工具载荷 |
| `POST /api/threads/{thread_id}/resume` | body 为 `{"request_id":"原请求 UUID"}`，恢复原生 checkpoint |
| `POST /api/chat/stream` | 与 chat 相同请求体，SSE 输出 |

未完成会话应先恢复，不能直接追加新问题。同一 thread 的并发执行返回 thread_busy。当前会话 admission 是单进程机制，**仅支持 workers=1**；不要用多进程共享这些数据库。

流式测试客户端：

```powershell
uv run --no-sync python scripts/stream_client.py --message '你好'
# 可选 --thread-id / --request-id；token 从 HEALTH_AGENT_CLIENT_TOKEN 环境变量读取。
```

SSE 事件：run.started、message.delta、tool.started、tool.finished、run.completed、run.failed。每帧含协议 version=1、递增 seq 和执行标识。最终 completed.answer 是权威回答。流建立后错误通过 run.failed 返回，HTTP 200 不代表执行成功。工具事件不包含参数 / 健康结果全文。断线时取消执行并保存已有 checkpoint；不支持 Last-Event-ID 事件重放，使用 request_id 恢复。

## 健康工具

九个基础健康工具：add_health_metric、query_health_metrics、add_diet_record、query_diet_records、add_exercise_record、query_exercise_records、query_health_documents、calculate_health_trend、search_health_knowledge。启用专业 Agent 后，Lead 另注册 delegate_health_task。

写工具接受嵌套 `record`，查询接受可选 `query`，例如模型工具参数：

```json
{"record":{"metric_type":"weight","value":70,"unit":"kg","measured_at":"2026-10-03T08:00:00+08:00"}}
```

指标单位：weight=kg、heart_rate=bpm、sleep_duration=hours、steps=count。饮食记录包含 food_name、amount、meal_type，营养值可空；运动 duration 为分钟、distance 为公里。用户未提供时间时使用当前 UTC，显式时间必须带时区。记录与幂等回执同一事务提交；查询按 owner 过滤。truncated=true 表示列表不完整；趋势独立查询区间内最多 10000 条，不能以截断列表替代全量统计。

工具统一返回 success / data / error_code / error_message / retryable；不提供删除或覆盖健康事实的工具。总超时、图步骤数、共享模型 / 工具预算和三次相同工具 / 参数 / observation 的停止规则已启用。只读工具对明确的瞬态失败进行有限指数退避与 jitter 重试；不自动重放写入。写超时的提交结果可能不确定，先核对记录并沿用原请求身份恢复。模型 SDK 重试、工具重试和 Agent 改变策略分别处理。

UI 接口：`GET /api/session` 返回可信身份与模式；`GET /api/records/{metric|diet|exercise}` 支持时间范围、指标类型和 limit；`POST` 同路径接受嵌套 `record` 与必填 UUID `request_id`，身份不从 body 读取。

## 专业 Agent 与可靠性

Lead 保留简单查询 / 写入的直接工具路径。复杂只读分析可调用 `delegate_health_task(agent, task)`，其中 agent 为 nutrition、record 或 research。三个子图均使用 LangChain `create_agent`：饮食分析仅读饮食与公共知识；记录分析仅读指标 / 运动 / 趋势；研究助手仅检索私人文档与公共知识。子图不包含写工具或委派工具，不继承完整聊天历史和持久化 thread 配置。

委派结果带 summary、实际工具 observations、截断标记和错误；Lead 汇总时把它作为待核对数据。可信身份、总预算和 trace 关联从服务端 context 传入，限制并发、委派次数、子图步骤和超时。工具尝试（包括只读重试）消耗共享预算，模型调用也有跨子图上限；SDK 内部重试不计作精确可见步骤。

保守规则对部分明确的紧急自述返回寻求急救的提示并跳过模型。规则不是临床分诊，不覆盖全部表达；真实模型回答质量与安全性仍需后续 Benchmark / 人工评估。

## 执行记录与 Trace

`GET /api/traces?thread_id=<UUID>&limit=20&offset=0` 列出当前用户执行，`GET /api/traces/{trace_id}` 返回摘要与时间线。对话下方的“查看执行记录”展示模型 / 工具 / 委派调用、可观测重试、耗时、token usage 和终止原因。恢复及幂等回放有独立 trace，仍关联原 request_id / thread_id。

Trace 使用 `health.db` 内独立的 `execution_traces` 表，只持久化固定允许的事件元数据，不保存问题、回答、健康原文、工具参数或原始异常。最多保存全局 1000 / 每用户 250 个 trace、单次 400 个事件；被裁剪事件有计数。Phase 12 要求已开始的模型/工具调用都有对应结束回调，才标记 capture_complete；工具超时仍可能缺少框架结束事件，此时明确显示不完整，不补造成功。进程中断后的 incomplete 记录不把未知调用数写成 0；token 缺失为 null。SDK 内部重试未必暴露，已观察重试数不等于所有网络尝试。

Trace 存储启动失败会拒绝执行；终态写入失败明确返回 trace_unavailable，已有业务写入和 checkpoint 不回滚，可沿原请求恢复。重启后遗留 running 记录标为 interrupted，丢失的内存事件明确标记不完整。

## 文档 RAG

| 接口 | 用途 |
| --- | --- |
| `POST /api/documents/text` | JSON：`{"filename":"notes.md","text":"..."}` |
| `POST /api/documents/upload` | multipart 的 file 字段，TXT / MD / PDF |
| `GET /api/documents` | 当前用户最近 100 个文档及解析 / 索引状态 |

UTF-8 TXT / MD、可提取文本 PDF；接受文件不超过 2 MiB、50 页、20 万字符、500 个片段。不含 OCR，扫描 / 空白 / 加密 PDF 会明确失败。失败记录保留状态，可重新上传同内容重试。相同用户 / 域 / 内容 / 索引版本去重，向量与 indexed 状态同一事务发布，不暴露部分索引。

默认 local_hash 是可解释的字符 / 词 n-gram embedding 和余弦向量检索，**不等同于神经语义模型**。Phase 12 增加原始词法特征交集检查，拒绝纯哈希碰撞导致的无共同词项召回；向量生成和索引版本保持兼容，既有索引不需重建。少量共享词但主题无关的误召回仍有待改进，provider 语义向量不使用此词法限制。向量存于 SQLite，先按私人 owner / 公共 visibility 过滤，再排序；最多读取 5000 个当前范围候选。结果带 citation_id、document_id、文件、页码、页内偏移、来源、索引版本与原文，模型引用实际片段。文档内容不会提升为系统指令。

可配置语义 embedding：

```dotenv
HEALTH_AGENT_EMBEDDING_MODE=provider
HEALTH_AGENT_EMBEDDING_MODEL=text-embedding-3-small
HEALTH_AGENT_EMBEDDING_DIMENSIONS=1024
```

此模式使用明确配置的 MODEL_BASE_URL / MODEL_API_KEY，会将文档片段送到所配置的服务。必须选择该服务支持的 embedding 模型与维度。切换模型、维度后需重新导入原文件，新索引版本不与旧向量混用。

普通 HTTP 用户不能发布公共知识。管理员在本机审核来源后导入：

```powershell
uv run --no-sync python scripts/ingest_public.py D:\your-reviewed-file.md --source '原始出版物标识或真实来源 URL'
```

项目不内置未经核验的医疗资料，不自动抓取来源 URL。

## 长期偏好 Memory

采用明确语句提取，支持“请记住：我喜欢清淡饮食 / 素食 / 不辣的食物 / 跑步 / 散步 / 游泳 / 骑行 / 瑜伽 / 简短的回答 / 详细的回答”，以及“以后请用中文回答”“以后请用英文回答”。这里斜线表示可选项，每次写一个具体偏好。

`GET /api/memory` 返回偏好、来源 request/thread 和允许值；`PUT /api/memory/{key}` 接受 `{"value":"允许值"}` 更正；`DELETE /api/memory/{key}` 忘记偏好。也可说“请忘记：我的运动偏好 / 饮食偏好 / 回答风格 / 语言偏好”。具体枚举由 API 返回。

只保存 allowlist 值，不保存健康测量、病史或原始对话。带引号的引用、否定和任意指令不会被提取。偏好变化在进入模型前落库并反馈 applied_changes，即使后续模型失败也可能已保存。查询根据当前问题选择饮食 / 运动偏好，风格 / 语言跨任务适用。偏好通过临时 HumanMessage 注入，不写入 checkpoint、不提高系统权限。request 回执防止恢复时复活已删除偏好。MEMORY_ENABLED=false 关闭 Agent 自动提取与注入；管理 API 仍可查看 / 删除已有偏好。

## 模型与配置

真实模型需支持标准 Chat Completions、tool calling 和流式协议：

```dotenv
HEALTH_AGENT_MODEL_MODE=provider
HEALTH_AGENT_MODEL_NAME=your-model-name
HEALTH_AGENT_MODEL_BASE_URL=https://api.openai.com/v1
HEALTH_AGENT_MODEL_API_KEY=your-key
```

失败不会自动降级 fake。完整配置见 [.env.example](.env.example)：默认总超时 60 秒、模型超时 20 秒、SDK 重试 1 次、max_steps=12、max_tool_calls=12、输入 8000 字符。默认数据路径 HealthAgent/data，含 health.db 与 checkpoints.db。数据库含私人信息与原始会话，应保护目录权限；当前只用 create_all 新建表，后续改变已有表结构需提供迁移。

错误返回固定 message 与 code，不回显原始异常。logging.json 关闭 access log，runtime 禁用自动外部 LangSmith tracing。Trace 为本地脱敏工程执行记录；Benchmark 的固定事实/引用规则仅是合成任务代理指标，不是临床准确率。

## Domain Benchmark 与优化

[benchmark/README.md](benchmark/README.md) 说明全部案例、运行参数、指标分母与比较规则。29 个案例覆盖 12 类任务，离线 contract 模式全部运行，真实 provider 模式执行适用的 22 个。每个案例建立独立临时 SQLite/checkpoint；真实模型只接收合成任务，不读取已有私人数据库。

从 backend 目录运行：

```powershell
.\.venv\Scripts\python.exe ../benchmark/runner.py --mode contract --repeats 2 --output ../benchmark/runs/my-contract-run
.\.venv\Scripts\python.exe ../benchmark/runner.py --mode provider --allow-provider --repeats 2 --output ../benchmark/runs/my-provider-run
```

评分结合实际 DB、模型工具提议、ToolResult、SQL 验证引用与持久 Trace；不会以回答自称成功判分。报告包含源码/用例/评分器/协议/设置指纹，可拒绝不可比较实验。contract 决策是脚本规定，工具选择/参数准确率记 N/A；模型连接失败也不能计作模型质量结论。`runs/` 保留本机实验，已审阅阶段证据见 `benchmark/results/`。

## 验证与阶段记录

```powershell
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest -q
uv run --no-sync python scripts/smoke.py
# 先构建前端、安装 Playwright Chromium，然后验证真实浏览器与真实本地 API：
uv run --no-sync python scripts/smoke.py --ui
```

前端验证（从 frontend 目录运行）：

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build
# 若 pnpm exec 在本机不可用，Windows 可执行 .\node_modules\.bin\playwright.CMD install chromium
pnpm exec playwright install chromium
pnpm test:e2e
```

浏览器契约测试通过合成 API 覆盖异常 / 恢复 / 身份切换；`smoke.py --ui` 则启动自己的 Uvicorn 与临时 SQLite，用构建后的页面走真实接口，结束后关闭服务器并清理临时数据。截图位于 gitignored 的 `frontend/test-results/real-ui/`。

默认测试禁止外部 HTTP，使用临时 SQLite、真实 LangGraph、可注入模型及 SDK MockTransport。smoke 启动自身 Uvicorn 子进程，在随机回环端口验证会话、SSE、文档和偏好，使用独立临时数据并关闭自身进程。

显式 `uv run --no-sync pytest -q -m live --run-live` 才调用真实 provider；缺配置时 skip。该 live 项是模型连接检查，不是完整工具 / RAG 质量评测。

- [Phase 2：工具与数据库](docs/phase-2-delivery.md)
- [Phase 3：会话与 checkpoint](docs/phase-3-delivery.md)
- [Phase 4：SSE](docs/phase-4-delivery.md)
- [Phase 5：RAG](docs/phase-5-delivery.md)
- [Phase 6：Memory 与最终验收](docs/phase-6-delivery.md)
- [Phase 7：Multi-Agent](docs/phase-7-delivery.md)
- [Phase 8：Reliability](docs/phase-8-delivery.md)
- [Phase 9：Frontend](docs/phase-9-delivery.md)
- [Phase 10：Trace / Observability](docs/phase-10-delivery.md)
- [Phase 11：Domain Benchmark](docs/phase-11-delivery.md)
- [Phase 12：Evaluation & Optimization](docs/phase-12-delivery.md)
- [架构](docs/architecture.md)、[规范](HEALTH_AGENT_SPEC.md)、[DeerFlow 源码研究](docs/phase-0-deerflow-analysis.md)

本地无 Git 元数据，不能提供提交 SHA / diff；没有修改参考仓库或引入 DeerFlow 依赖。
