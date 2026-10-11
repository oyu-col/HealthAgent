- 对应目录：`benchmark/cases/`
- 核对日期：2026-10-11
- 实际目录：[cases/](../../../benchmark/cases/)

# 合成任务语料与独立判分条件

## 目录职责

当前只有[health-v1.json](health-v1.json.md)，保存29个公开合成案例。它同时提供环境准备所需事实、待执行的用户问题，以及判分器使用的期望；各字段有不同接收者，不能因为存于同一JSON就全部注入模型。

## 三种数据的分离

initial_environment进入环境Service以建立实际SQLite记录和文档索引。input进入真实对话请求。execution_plan只进入contract模型；expected_state、expected_arguments、expected_observations、expected_evidence和答案约束只进入判分器。

provider模式不读取execution_plan来决定动作；contract模式不能读取expected字段生成“标准答案”。这种分离在[runner集成测试](../../backend/tests/integration/test_benchmark_runner.py.md)中通过修改oracle但保持实际执行结果验证。

## 维护约束

新增任务应有独立可核验的DB、工具或证据目标。负例不能只依赖一句“无依据”：还要检查真实检索结果、禁止文档和引用数。日期使用固定绝对时间，避免自然日变化污染基线。

案例变更会改变case_digest。正式比较要求两次使用完全相同的案例协议；发现grader/fixture问题应修复后重跑基线，不能只更新candidate。

