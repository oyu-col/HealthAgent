- 对应目录：`backend/tests/unit/`
- 核对日期：2026-10-11
- 实际目录：[unit/](../../../../backend/tests/unit/)
- 上级说明：[目录说明](../README.md)

# 后端核心边界单元测试目录

## 目录定位

这里集中验证配置、模型工厂、Runtime 输出/错误、Trace 记录器，以及 Phase 11–12 的案例结构、独立判分和实验比较规则。许多测试仍使用真实框架对象，少数涉及临时 SQLite；unit 是组织方式，不表示所有测试都只调用纯函数。

## 共同执行条件

pytest 使用 backend/tests/conftest.py 提供的受控 Settings/临时目录，并使用 tests/fakes.py 的合成模型。不读取真实健康数据，不自动访问付费 provider。修改环境使用 monkeypatch 保证恢复，异步资源通过上下文退出。

## 核心约束

配置测试阻止隐式模式、越界预算、危险 URL 与秘密回显；模型工厂测试保证选择和 HTTP 资源所有权；Runtime 测试保证真实框架 context、可见最终答案、超时/取消和脱敏；Trace 测试保证计数不重复、晚到 usage 可合并、事件白名单和有限保留。

Benchmark 测试增加独立的评分协议约束：案例字段严格校验、禁止把脚本决策当模型质量；状态/证据/Trace 任一错误不能被漂亮回答掩盖；未知分母不能伪造零，未完成或协议不同的实验不能比较。数值与 citation 的 token 边界也有回归测试，防止随机标识误伤真实任务。

## 与集成/评测的区别

此处正确并不自动证明会话恢复、工具真实入库、检索权限或浏览器行为，后者由 integration 与前端测试负责。合成模型的固定回答不是医学正确性评测；真实 provider 质量仍需要显式在线和领域评测。

## 阅读与运行

建议先读 test_config 和 test_model_factory，再读 test_runtime 与 test_trace_recorder；阅读评测时按 test_benchmark_cases → test_benchmark_graders → test_benchmark_report 前进。可从 backend 运行 pytest tests/unit。目录说明介绍覆盖目的；实际执行情况应看当前测试输出与阶段验收，不能以文档存在替代测试通过。

## 文件导航

- [test_config.py](test_config.py.md)：配置校验与敏感信息保护单元测试。
- [test_runtime.py](test_runtime.py.md)：Runtime 真实图调用、输出过滤与错误边界测试。
- [test_model_factory.py](test_model_factory.py.md)：模型选择与 HTTP 客户端清理测试。
- [test_trace_recorder.py](test_trace_recorder.py.md)：Trace 去重、脱敏、容量与重启行为测试。
- [test_benchmark_cases.py](test_benchmark_cases.py.md)：29 个案例的结构、覆盖范围与模式安全边界。
- [test_benchmark_graders.py](test_benchmark_graders.py.md)：真实状态和引用判分的反自证、数字/标识误判回归。
- [test_benchmark_report.py](test_benchmark_report.py.md)：指标真实分母、失败保留、完整样本与同协议比较。

