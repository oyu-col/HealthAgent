# conftest.py：离线隔离与测试配置

- 对应源码：`backend/tests/conftest.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[conftest.py](../../../backend/tests/conftest.py)

## 主要 hook 与 fixture

pytest_addoption 注册 --run-live，默认不启用。pytest_collection_modifyitems 在未开启时对带 live marker 的测试加 skip。marker 本身由 pyproject 注册，显式开关保证普通 pytest 不意外调用计费服务。

autouse 的 isolate_environment_and_network 对 live 项放行；其他测试清理 HEALTH_AGENT_、OPENAI_、LANGSMITH_、LANGCHAIN_ 前缀环境变量，并显式设置 LANGSMITH_TRACING=false，减少继承机器配置造成外部连接或追踪的风险。

该 fixture patch httpx.HTTPTransport.handle_request、AsyncHTTPTransport.handle_async_request 以及 requests.Session.request，使真实 HTTP transport 调用直接断言失败。ASGITransport 和 MockTransport 可继续使用，因此既能离线测试 API/SDK，又能发现误联网。它不是系统防火墙，不能宣称阻止所有库的一切 socket。

settings fixture 创建 fake Settings，data_dir 指向 tmp_path，_env_file=None 防止读取项目 .env。测试需要 provider 配置时用显式合成值替换字段，不能借用开发者秘密。

## 设计与维护

共享隔离放在 conftest 可避免每个测试漏清理一遍环境。monkeypatch 在测试结束后还原，不能依靠测试顺序保留状态。新增网络 SDK 时应检查其底层 transport 是否受此约束。真实 Uvicorn smoke 是独立脚本，不在此 autouse fixture 下运行，靠自己的临时配置和进程管理隔离。
