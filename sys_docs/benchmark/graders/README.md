- 对应目录：`benchmark/graders/`
- 核对日期：2026-10-11
- 实际目录：[graders/](../../../benchmark/graders/)

# 独立规则判分器

## 职责与边界

这里接收case的expected字段及runner从真实执行构造的observation。判分器不调用模型，不运行健康工具，不读取execution_plan，也不接受模型一句“成功”替代数据库和Trace。

当前只有[task.py](task.py.md)实现task_v1规则，[__init__.py](__init__.py.md)导出grade_case。规则涵盖业务状态、真实工具执行、参数、跨用户隔离、引用来源及有限回答约束。

## 与模型和报告的关系

contract和provider使用相同业务检查；但固定决策不能算模型质量，所以contract的工具选择与参数指标分母为0。provider连第一条模型响应都未取得时仍记任务失败，质量分母归零并标识基础设施失败。

输出只包含检查名称、布尔值、失败类别和数值计分，不返回原始健康载荷。实际结果汇总交给[report](../report.py.md)。

## 修改要求与验证

grader的任何改动都改变grader_digest，不能与旧基线直接比较。先用[反自证测试](../../backend/tests/unit/test_benchmark_graders.py.md)证明错误数据能被拒绝，再建立新基线。测试应覆盖“答案正确但数据库空”“存在工具提议但未执行”“伪引用”“随机UUID数字误命中”等独立负例，不能只重复规则的成功路径。

