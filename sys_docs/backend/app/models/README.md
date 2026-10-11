- 对应目录：`backend/app/models/`
- 核对日期：2026-10-04
- 实际目录：[models/](../../../../backend/app/models/)
- 上级说明：[目录说明](../README.md)

# 模型适配与客户端生命周期层

## 职责

给领域 Agent 提供统一 BaseChatModel，集中选择明确的 fake/provider 模式，并由应用生命周期拥有 SDK 使用的 HTTP 客户端。此目录不定义健康工具、不维护聊天历史，也不通过导入副作用联网。

## 两种模式

fake 使用 DemoChatModel，明确标识、只回显最后用户消息，不自主调用工具。provider 使用 ChatOpenAI，显式传 Settings 中的模型名、URL、密钥、时限和重试，当前选择 Chat Completions 路径。
模式选择不会自动因 provider 故障退回 fake，响应/UI 可据 model_mode 告知用户执行性质。框架、数据库和表单在 fake 模式仍实际运行。

## 生命周期和错误

main.py 的 lifespan 进入 model_session；正常 shutdown 或构造失败都会关闭 sync/async httpx 客户端。运行时网络/SDK 错误由 Runtime 安全映射；工厂构造成功并不证明远端兼容或在线可用。

## 阅读、验证与修改

先读 factory，再读 demo。test_model_factory 验证显式配置和资源清理；test_provider_transport 用真实 SDK+本地 HTTP mock 验证协议；live 验证另有显式开关。升级 SDK 或切换 API 前检查流式/工具调用兼容，不能只运行 fake 冒烟。

## 文件导航

- [__init__.py](__init__.py.md)：模型适配包入口。
- [demo.py](demo.py.md)：明确标识的本地演示回显模型。
- [factory.py](factory.py.md)：模型工厂与 provider HTTP 客户端生命周期。

