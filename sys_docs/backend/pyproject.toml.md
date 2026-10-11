# pyproject.toml：Python 工程、依赖和检查入口

- 对应源码：`backend/pyproject.toml`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[pyproject.toml](../../backend/pyproject.toml)

## 工程与打包

项目名 health-agent、版本 0.1.0，Python 要求 >=3.12,<3.15，构建后端为 hatchling，wheel 仅包含 app 包。uv 通过该文件解析依赖并安装独立工程；它不引用 DeerFlow workspace 或继承其全部包。

## 依赖分组的作用

FastAPI/Uvicorn 提供 Web；Pydantic/pydantic-settings 处理数据和配置；LangChain、langchain-core、LangGraph 提供标准 Agent/消息/图；langchain-openai、OpenAI、httpx 提供明确 provider 客户端；langsmith 用于与框架 tracing context 配合并明确关闭外部自动追踪，不等于启用云端追踪。

SQLAlchemy asyncio、aiosqlite 管业务库，langgraph-checkpoint-sqlite 管官方 checkpoint。langchain-text-splitters 做切分，pypdf 提取文本，python-multipart 接收上传，tzdata 支持 Windows 等环境的时区。dev 组包括 pytest、pytest-asyncio、Ruff。

版本区间是允许解算的范围，实际版本由 [uv.lock](uv.lock.md) 决定。升级时不能只看声明下界推断 API 可用性，应验证真实 create_agent、ainvoke/astream 版本参数及 SDK 协议。

## 测试与质量设置

pytest 从 tests 收集，asyncio_mode=auto，默认附 -ra，并将 basetemp 放到项目内 .pytest-tmp，避免依赖 Windows 系统临时目录权限。live marker 明示需要手动开启的真实服务检查，具体跳过逻辑在 [conftest.py](tests/conftest.py.md)。

Ruff 目标 py312、行宽 100，排除 .pytest-tmp，启用 E/F/I/UP/B/ASYNC 规则。格式与静态检查不能替代业务断言。修改依赖、解释器范围或检查策略时，同步 lockfile、启动文档和实际验证记录。
