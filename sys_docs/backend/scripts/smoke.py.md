# smoke.py：真实本地 HTTP 和可选浏览器闭环

- 对应源码：`backend/scripts/smoke.py`
- 核对日期：2026-10-11
- 目录导航：[本目录说明](README.md)
- 源码：[smoke.py](../../../backend/scripts/smoke.py)

## 为什么还需要 smoke

ASGI 测试不能完全覆盖实际端口监听、Uvicorn lifespan、TCP SSE、静态构建资源和进程退出。该脚本启动自己的服务，使用正式 API 与临时 SQLite 验证这些环节，并在清理全部完成后才打印 passed JSON。

## 准备与隔离

先在 127.0.0.1 绑定临时端口取得可用号码，随后释放并启动服务；这不是持有 socket 的原子端口移交，若竞争占用则通过启动/就绪失败报告。清理继承环境的 HEALTH_AGENT_* 项，显式选择 fake/local/local_hash、开启 Memory、设置 PYTHONUTF8 和临时 DATA_DIR。

在 backend 创建 .smoke-* TemporaryDirectory 与临时日志文件，解析确认数据路径留在 backend 内。Windows 子进程使用 CREATE_NO_WINDOW。它启动 [smoke_server.py](smoke_server.py.md)，不复用或关闭用户已有服务。

隔离范围有限：这里只清理父进程 HEALTH_AGENT_* 环境变量并覆盖上述指定项，子服务的 Settings 仍读取项目根 .env。未被覆盖的 local_user_id、时区、超时、预算等配置仍可影响 smoke，不能将其描述为完全独立于 .env 的配置环境。

## 实际断言

用 trust_env=False 的 HTTP 客户端最多等待 30 秒就绪。验证 /healthz 的 phase=12/model_mode=fake，OpenAPI 包含 chat；发送明确偏好语句并确认 fake 标识、trace header、两条历史及保存偏好；上传合成 Markdown 并确认 indexed；沿原 thread 进行 TCP SSE，验证 started/completed 以及四条历史；删除偏好并确认空；读取持久 Trace，确认 completed 和可观察模型调用。

这里的 phase=12 断言与当前 HealthResponse 协议一致，作用是发现启动了旧版本或错误服务。源码中的 SSE 合成消息仍写作“Phase 10 流式启动验证”；它只是输入文本，不参与阶段判定或评测计分，不能据此把运行版本解释为 Phase 10。

--ui 还调用 frontend/scripts/smoke.mjs，让构建后的真实页面连接同一个临时后端，子进程限时 90 秒，将 JSON 浏览器结果纳入报告。需要先构建前端并准备浏览器运行依赖。

## 退出和失败语义

finally 写 stop 文件，请服务优雅退出，等待 15 秒；必要时仅终止自己启动的进程树，并等待结束。非零退出码视为失败；随后再次探测端口必须不再监听。TemporaryDirectory 退出完成清理后才输出最终报告，所以“接口断言通过但进程/文件未清理”不会被记为整个 smoke 成功。

日志用于子进程诊断；报告只含检查名、端口、trace_id 和可选浏览器结果。此流程没有真实 provider 规划或医学质量断言，不代替完整 pytest/浏览器契约测试。

Phase 11/12 的固定案例评测、冻结基线和优化前后比较由独立 benchmark runner/report 负责，本脚本继续承担实际进程、HTTP/SSE 与可选浏览器的运行验证；健康探针返回 12 并不等于执行了领域评测。
