# config.py：配置契约与启动校验

- 对应源码：`backend/app/config.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[config.py](../../../backend/app/config.py)

## 入口与读取规则

`PROJECT_ROOT` 由源码路径 parents[2] 确定；`Settings(BaseSettings)` 固定读取项目根 .env，编码 UTF-8，变量前缀 `HEALTH_AGENT_`，同名环境变量优先。Settings 冻结，禁止额外字段、NaN/Infinity，并隐藏验证错误中的输入。显式传参和测试的 `_env_file=None` 可避免读取开发者配置。

`model_mode` 必填且只能 fake/provider，不能依赖默认 provider 或静默降级。下表的字段省略环境变量前缀，默认值来自当前代码，**并非读取本机 .env 得到的有效配置**。

| 字段 | 默认 / 约束 | 控制对象 |
| --- | --- | --- |
| MODEL_MODE | 必填 fake/provider | 模型路径 |
| MODEL_NAME、MODEL_BASE_URL、MODEL_API_KEY | 默认空；provider 时必填 | 明确的服务地址、模型和密钥 |
| REQUEST_TIMEOUT_SECONDS | 60，>0 且 ≤300 | 完整运行总时限 |
| MODEL_TIMEOUT_SECONDS | 20，>0 且 ≤300，不超过总时限 | 单次模型客户端等待 |
| MODEL_MAX_RETRIES | 1，0–2 | SDK 内部有限重试 |
| MAX_STEPS | 12，2–100 | 图步骤限制及相关运行预算 |
| MAX_INPUT_CHARS | 8000，1–32000 | 对话文本长度；另有 HARD_INPUT_LIMIT=32000 |
| MAX_TOOL_CALLS | 12，1–100 | 共享工具尝试上限 |
| LOCAL_USER_ID | local-user，1–64 字符 | local 模式的服务端身份 |
| TIMEZONE | Asia/Shanghai，合法 ZoneInfo | 可信时区上下文 |
| DATA_DIR | PROJECT_ROOT/data | SQLite 数据根目录 |
| AUTH_MODE | local/token，默认 local | 身份验证模式 |
| API_TOKENS | 默认空映射，值为 SecretStr | user_id → token 的服务端映射，认证时反向匹配 |
| EMBEDDING_MODE | local_hash/provider，默认 local_hash | 词面基线或显式远程 embedding |
| EMBEDDING_MODEL | 默认空，非空时长度限制 | provider embedding 模型 |
| EMBEDDING_DIMENSIONS | 1024，128–3072 | 向量维度及索引版本 |
| MEMORY_ENABLED | true | Agent 自动提取与注入偏好 |
| SUBAGENTS_ENABLED | true | 是否注册专业委派 |
| MAX_DELEGATIONS | 3，1–6 | 当前运行委派次数 |
| SUBAGENT_MAX_CONCURRENCY | 2，1–4 | 专业任务并发 |
| SUBAGENT_TIMEOUT_SECONDS | 20，>0 且 ≤120 | 含等候的专业任务时限 |
| SUBAGENT_MAX_STEPS | 8，2–50 | 子图步骤限制 |
| TOOL_TIMEOUT_SECONDS | 10，>0 且 ≤120 | 工具实际尝试时限 |
| TOOL_MAX_RETRIES | 2，0–3 | 只读瞬态失败重试 |
| TOOL_RETRY_INITIAL_DELAY | 0.1，0–5 | 初始退避时间 |

## 校验为何放在启动阶段

provider 聊天模式必须同时具备模型名、URL 和去空白后非空密钥；embedding provider 要求 embedding 模型、URL 与密钥字段具有真值，即使聊天处于 fake 模式也会执行此检查。当前 embedding-only 分支没有聊天 provider 分支相同的密钥去空白检查，不能把两者描述为完全等价的校验。URL 允许 HTTP(S)，但禁止用户名/密码、query 和 fragment，减少把凭据混入地址的机会。

token 模式要求非空映射；用户标识非空且受长度限制，token 至少 16 字符且不能重复，否则两个 owner 共享同一凭据将产生歧义。model_name 和 local_user_id 会 strip 并拒绝空白；embedding_model 当前仅有长度及 provider 分支真值检查，没有 strip validator。时区必须能被 ZoneInfo 解析。

密钥用 SecretStr，URL、凭据字段在 repr 中隐藏；`load_settings()` 将配置错误转换为固定 RuntimeError，不把 Pydantic 原始输入或秘密拼接进日志。直接构造 Settings 时仍应遵守不打印配置对象的惯例。

## 配置与功能的关系

参数只定义约束，实际执行在 Runtime、reliability、子 Agent 和 embedding 模块。例如开启 Memory 不意味着任意健康事实都会记忆；关闭自动记忆也不自动删除数据库里的偏好。更改 embedding 模型/维度会形成不同索引版本，需要重新导入原文档。

关联：[公开样例](../../.env.example.md)、[本地配置说明](../../.env.md)、[配置测试](../tests/unit/test_config.py.md)。新增配置应同步三处：本文件验证规则、样例说明、消费它的业务模块及测试。
