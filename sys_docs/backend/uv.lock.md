# uv.lock：可复现的 Python 依赖解算

- 对应源码：`backend/uv.lock`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[uv.lock](../../backend/uv.lock)

这是 uv 生成的依赖锁，采用 lock schema version=1，记录 >=3.12,<3.15 的 Python 范围以及完整 package、来源、依赖关系、条件 marker、wheel/sdist 信息和校验值。它覆盖应用和开发依赖，是本工程独立解算的结果。

[pyproject.toml](pyproject.toml.md) 声明想依赖什么版本范围；lockfile 指定实际解算组合。使用 uv sync --locked 可拒绝声明与锁不一致，--offline 只有所需包已在缓存时才有意义，不能保证全新机器无网络完成安装。

不应手工逐条修改版本或复制 DeerFlow 的锁文件。依赖变更后由 uv 重新解算，再运行对应图执行、数据库、HTTP/SSE 与 SDK MockTransport 测试；真实 provider 能力仍需要单独联调。

本文件不保存用户健康数据、聊天历史或 .env 密钥。它也不证明所有兼容服务都支持 tool calling/streaming，只能使已验证的 Python 依赖组合更可复现。逐项第三方包的内部实现不在本套项目源码说明范围。
