- 对应源码：`benchmark/graders/__init__.py`
- 核对日期：2026-10-11
- 阅读源码：[__init__.py](../../../benchmark/graders/__init__.py)
- 所属目录：[目录说明](README.md)

# 规则判分包的明确导出

## 实际作用

文件声明这是依据真实运行与数据库证据工作的确定性判分包，从.task导入grade_case，并以__all__只公开该入口。它不注册远程judge，也不读取配置或执行案例。

## 设计目的

将判分与runner、模型明确分层，调用者只需传入case和observation，取得稳定JSON安全结果。新增其他grader时应显式定义版本与选择规则，不能在此根据结果好坏自动选择更宽松判分器。

## 关联

判分实现见[task.py](task.py.md)，运行方见[runner.py](../runner.py.md)。本文件也属于runner计算的grader源码指纹范围，修改后会影响可比性。

