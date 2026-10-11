# live：显式联网验证

- 对应目录：`backend/tests/live/`
- 核对日期：2026-10-04
- 实际目录：[live](../../../../backend/tests/live)

本目录目前只有 [test_provider.py](test_provider.py.md)，用于具备真实配置时检查 provider 模型链路。它与默认离线单元/集成测试分开，通过 live marker 和 --run-live 双重表达运行意图；缺配置时跳过，不能把 skip 当作通过。

本目录不包含完整工具规划、RAG 命中、专业委派或医学安全 Benchmark。开启后会实际调用配置服务，应使用适合验证的非敏感输入，并遵守测试文件自身的配置与断言。默认不联网的 hook 在 [conftest.py](../conftest.py.md)，具体运行命令见项目 README。
