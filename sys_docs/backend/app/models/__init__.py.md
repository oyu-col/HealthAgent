- 对应源码：`backend/app/models/__init__.py`
- 核对日期：2026-10-04
- 阅读源码：[__init__.py](../../../../backend/app/models/__init__.py)
- 所属目录：[目录说明](README.md)

# 模型适配包入口

## 当前作用

仅包含 `Model adapters owned by HealthAgent.` 包级字符串，无导入副作用、网络调用或模型单例。HealthAgent 的模型选择和资源生命周期在 factory.py，回显模型在 demo.py。

## 设计目的

让领域 Agent 依赖 BaseChatModel 接口，而不是到处直接创建 provider SDK。不要在此处添加自动“真实模型失败后改 fake”的回退；当前运行模式必须显式配置并在响应/UI 中可辨认。

## 相关源码说明

- [backend/app/models/factory.py](factory.py.md)
- [backend/app/models/demo.py](demo.py.md)

