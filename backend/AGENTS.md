# HealthAgent 后端开发约定

继承项目根 AGENTS.md 和 HEALTH_AGENT_SPEC.md。后端是独立包 `health-agent`，源码导入前缀为 `app`，不引用 DeerFlow。

- 从本目录运行命令；配置固定读取 HealthAgent 根目录 `.env`，测试使用 `_env_file=None` 并清除配置环境变量。
- 应用通过 `create_app` 构建，lifespan 拥有模型 / embedding HTTP 客户端、SQL engine 和 checkpointer；导入模块不联网。
- 使用 `create_agent` 和公开 `context=`；`ainvoke(version="v1")` 返回 dict，`astream(version="v2")` 返回 StreamPart；更换格式必须同步测试。
- Phase 2–10 的 Thread / RAG / Memory / 专业 Agent / Reliability / Trace 已实现；同请求用 request_id 去重，失败用 checkpoint 恢复。部署仅支持一个 worker。
- 子 Agent 仅只读 allowlist，无递归委派；可信 RunContext 共享预算并注入身份，不能继承完整父会话或模型指定身份。
- 瞬态只读重试复用框架 ToolRetryMiddleware；写入结果不确定时不自动重放，取消必须传播。
- Trace 通过公开 callbacks 和领域 hooks 记录白名单元数据；不持久化问题、健康原文、工具参数、原始异常；不可见 usage / 重试不能伪造为零。
- 工具身份从 ToolRuntime 注入；检索在 SQL 层先过滤 owner / visibility；不得开放普通用户写公共知识库。
- Memory 只存 allowlist 偏好；注入采用临时 HumanMessage，不能保存为 SystemMessage 或混入 checkpoint 历史。
- 单元与集成测试默认不联网；真实 provider 测试必须显式 `--run-live`，缺配置时明确 skip。
- Phase 11 独立 Benchmark 从本目录运行 `../benchmark/runner.py`；真实评测另需 `--mode provider --allow-provider`。遵守冻结协议比较；contract 工具决策脚本化，不代表模型能力。
- 修改前先添加对应行为测试，再修改实现。失败消息与日志禁止带原始异常、密钥、prompt 或完整 state。
- 校验：`.venv/Scripts/python.exe -m pytest -q`、`.venv/Scripts/ruff.exe check .`、`.venv/Scripts/ruff.exe format --check .`；也可使用 `uv run --no-sync`。
