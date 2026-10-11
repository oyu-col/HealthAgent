# backend：后端工程目录

- 对应目录：`backend/`
- 核对日期：2026-10-04
- 实际目录：[backend](../../backend)

## 功能与设计目的

本目录是独立的 Python 项目，负责可信身份、Agent 执行、健康数据和文档检索，并提供 FastAPI HTTP/SSE 接口。它使用自己的 pyproject、uv.lock 和虚拟环境，运行不 import 同级 DeerFlow。独立锁依赖可避免参考仓库的插件、沙箱与大型部署依赖扩散到本项目。

| 入口 | 职责 |
| --- | --- |
| [app/](app/README.md) | 应用装配、API、运行机制和业务实现 |
| [tests/](tests/README.md) | 单元、真实框架/SQLite 集成及显式 live 测试 |
| [scripts/](scripts/README.md) | 本地启动验证、SSE 客户端、公共资料导入与交付核对 |
| [pyproject.toml](pyproject.toml.md) / [uv.lock](uv.lock.md) | 依赖声明、可复现解算、包构建和测试/Lint 设置 |
| [logging.json](logging.json.md) | Uvicorn 和应用的固定日志配置 |
| [.python-version](.python-version.md) | 工具默认选择 Python 3.12 |
| [AGENTS.md](AGENTS.md.md) | 后端变更、验证和隐私约定 |

## 启动到请求的流程

从本目录以 Uvicorn factory 模式加载 `app.main:create_app`。配置文件固定在项目根目录，数据目录默认在项目根 `data`，并非随着当前终端目录任意变化。lifespan 创建数据库、官方 checkpointer、模型客户端、图和服务，HTTP 请求再从 app.state 取得这些长期资源。

自然语言入口通过会话服务和 Runtime；健康表单、偏好管理及文档上传可直接调用 Service。两类入口共享身份、领域校验和 Repository，避免产生两套数据规则。详情参见 [main.py](app/main.py.md)。

## 部署和维护边界

当前要求 `--workers 1`：进程内 Thread admission 和容量锁不提供跨进程协调。业务库和 checkpoint 库分别管理，不能把整个健康任务理解为跨两个文件的事务。SQLAlchemy 当前使用 create_all 建表，不包含已有表字段变更的自动迁移体系。

`.venv`、测试缓存和临时 smoke 数据不是源码，所以不建立逐文件说明。后端演示模式及离线测试验证工程流程；真实 provider 联调需要显式配置，不能把默认跳过当成验证成功。
