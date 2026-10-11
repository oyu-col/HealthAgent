# HealthAgent Domain Benchmark

此目录实现 Phase 11 的任务评测与 Phase 12 的前后对比。版本一有 **29 个合成任务、12 类场景**；每次实际创建隔离的 SQLite、checkpoint、健康 Service、文档索引及 LangGraph 图。评测不使用现有 `data/`。

## 两种执行模式

| 模式 | 任务数量 | 用途与限制 |
| --- | --- | --- |
| `contract` | 29 | 固定模型决策，真实执行工具、数据库、检索和故障注入。验证工程契约，不能衡量模型自主规划；工具选择/参数准确率为 N/A。 |
| `provider` | 22 | 使用根 `.env` 中显式配置的真实模型；模型只看用户输入、工具 schema 和真实 observation，不接收标准答案或脚本计划。 |

7 个仅限 contract 的任务用于可重复的故障、循环及哈希碰撞回归。provider 报告在 `profile_excluded_cases` 明确列出它们，不将未执行案例当作通过。两种模式都使用本地 `local_hash` 文档索引；真实模型评测不等于在线 embedding 评测。

## 运行

从 `HealthAgent/backend` 执行；现有开发依赖已经包含全部评测依赖：

```powershell
.\.venv\Scripts\python.exe ../benchmark/runner.py --mode contract --repeats 2 --output ../benchmark/runs/my-baseline-contract
# 真实请求会产生模型服务调用。必须同时显式选择 provider 与 allow-provider。
.\.venv\Scripts\python.exe ../benchmark/runner.py --mode provider --allow-provider --repeats 2 --output ../benchmark/runs/my-baseline-provider
# 仅运行一个适用于该模式的案例：
.\.venv\Scripts\python.exe ../benchmark/runner.py --mode provider --allow-provider --case-id query_owner_weight --output ../benchmark/runs/my-connection-check
```

每个输出目录必须不存在，已有结果拒绝覆盖。可用 `--cases` 指定兼容 schema 的 JSON，`--case-id` 可重复，`--repeats` 为 1–3，`--seed` 默认 20261011。运行逐案例保存 `report.json`，全部执行完成再设置 `manifest.completed=true` 并生成 `report.md`。退出码 0 表示所有案例通过，1 表示案例含失败，2 表示启动配置/参数错误。未完成报告不可用于前后对比。

每个案例总请求上限 90 秒、模型超时 30 秒、SDK 自动重试 0、工具预算 12、模型预算 16、子图步骤 8、模型输出上限 1200 tokens；特殊故障案例可在 schema 允许范围内覆盖设置。Runner 外层再限制单案例 220 秒。完整默认值见 `runner.py:BASE_SETTINGS`；服务实际的计费规则另由服务方决定。单任务仍可能包含多个模型请求，委派共享预算。

## 案例、执行与独立判分

- `cases/health-v1.json`：输入、种子环境、期望数据库状态、必需/禁止工具、参数与 observation 断言、回答和引用约束；覆盖查询、写入、RAG、多工具、多 Agent、缺参、歧义、工具失败、超时、恢复、安全与循环。
- `schema.py`：Pydantic 严格结构校验、默认值、唯一 ID、任务类别及模式边界；未知字段拒绝。
- `environment.py`：通过实际 Service 写入合成种子、索引文档，在单个 app 实例注入和恢复故障。
- `model.py`：contract 模型只读 `execution_plan`；结束时回显真实 ToolMessage。它不访问 expected 字段。脚本明确指定澄清措辞的场景只证明链路可处理该行为。
- `runner.py`：临时应用生命周期、真实 `/api/chat` / replay / resume、checkpoint、判分、指纹和增量报告。
- `observation.py`：内存采集真实模型工具提议和 ToolResult；直接读 SQL 快照；把 citation 与当前 owner/visibility 范围内实际 indexed chunk 的文字、来源版本核对。
- `graders/task.py`：独立地比较实际状态与期望；不能因回答“已成功”判成功。其他用户数据必须保持不变；集合断言防止查询夹带额外用户行。
- `report.py`：带明确分母的统计和严格前后对比。不能因改变评测案例、评分器或预算而声称优化有效。

## 指标解释

| 指标 | 实际分母 / 可解释范围 |
| --- | --- |
| task_success | 全部已执行案例；DB、必要工具、实际 Trace、回答/证据约束同时通过。失败不剔除。 |
| tool_selection | provider 的必需及禁止工具断言覆盖率；不是所有调用的 precision。contract 不计。 |
| tool_arguments | provider 对规定工具实际提出的每次参数校验；先错后对记一次错一次对，缺必需调用记失败。 |
| tool_execution | 已观测到 `tool.finished` 的实际尝试成功率；包含重试与故障注入的失败。 |
| tool_terminal_coverage | finished / started；指出超时或取消造成的结束事件缺口，不能把不可见结果当作成功。 |
| recovery | 实际触发可恢复注入故障的合格任务成功率；单纯幂等回放另以任务成功判定，不充当异常恢复。 |
| loop / unexpected_loop | `no_progress` 终态占比；后者排除刻意制造循环的案例。 |
| tool_calls / agent_steps | 完整 Trace 的累计模型/工具调用数，包含子 Agent；显示实际样本数，不是 LangGraph super-step 数。 |
| latency_ms / agent_latency_ms | 前者包括建库/准备的案例墙钟耗时，后者为持久 Trace 执行耗时；报告均值、总体标准差、极值和样本数。 |
| retrieval_hit / grounded_answer | 目标文档、无证据约束、实际引用来源与固定关键事实的规则代理；不代表医学事实全面正确。 |
| token_usage | 仅累加模型实际报告的 usage；缺少时 null，完整性独立标记，不估算成本。 |

纯数字回答约束按独立数值匹配，避免把随机 UUID 中的数字误认为健康值；引用 ID 也必须有正确的 token 边界。无适用分母显示 N/A。模型尚未返回即连接失败时，任务保持失败并增加 Infrastructure Error，而工具选择/参数及回答质量不计分，不能将服务不可用当作模型能力结论。

## 复现优化

先保存基线，再修改业务代码，使用相同命令的全新输出目录运行 candidate：

```powershell
.\.venv\Scripts\python.exe ../benchmark/report.py ../benchmark/runs/my-baseline-contract/report.json ../benchmark/runs/my-candidate-contract/report.json --output ../benchmark/runs/my-comparison.json
```

比较器要求案例、grader、运行协议、设置、Python、依赖、模式、种子、选中任务与重复次数一致，且每个样本恰好出现一次。只允许业务 app 源码指纹不同。它输出 improved、regressed 和 unchanged_failures；固定温度与种子仍不能保证远端服务完全确定。两轮小样本的耗时差异不能单独证明性能提高。

没有 Git 元数据时使用 SHA-256；`app_digest` 覆盖 app 下全部 Python 文件，`protocol_digest` 覆盖六个运行/观察/报告/schema 文件。不要修改结果里的指纹以绕过比较检查。

## 数据与结果

加载真实 provider 配置后，Runner 暂时清除其他 HealthAgent / OpenAI / LangSmith 环境变量并关闭外部 tracing，只传入必要模型配置；结束恢复环境。每案例临时目录随生命周期清理。不会向 provider 发送既有私人数据库内容。案例是公开的合成夹具。

报告保存检查结果、种子文档 key、计数和白名单 Trace 元数据，不保存问题回答全文、工具参数、原始异常、服务 URL 或密钥。内存中的原始 observation 仅用于本次判分。`runs/` 是忽略提交的实验输出；经审阅的阶段结果可放入 `results/`。详细交付、失败分析和实际执行记录见项目 `docs/phase-11-delivery.md`、`docs/phase-12-delivery.md`。
