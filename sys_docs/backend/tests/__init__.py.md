# tests/__init__.py：测试包入口

- 对应源码：`backend/tests/__init__.py`
- 核对日期：2026-10-04
- 目录导航：[本目录说明](README.md)
- 源码：[__init__.py](../../../backend/tests/__init__.py)

当前文件为空。它仅使 tests 成为可导入的包，便于用 tests.fakes 等路径共享测试模型；没有 fixture、测试用例、资源创建或隐藏初始化逻辑。

公共 fixture 在 [conftest.py](conftest.py.md)，可控模型在 [fakes.py](fakes.py.md)。新增测试支持代码应放入职责明确的模块，避免在包导入时创建数据库或读取 .env。
