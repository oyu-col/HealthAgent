- 对应源码：`backend/tests/unit/test_benchmark_cases.py`
- 核对日期：2026-10-11
- 阅读源码：[test_benchmark_cases.py](../../../../backend/tests/unit/test_benchmark_cases.py)
- 所属目录：[目录说明](README.md)

# 案例集结构与安全边界单元测试

## 定位

本文件验证[benchmark/schema.py](../../../benchmark/schema.py.md)与版本化案例集的输入契约，避免因拼错字段、错模式或错误oracle让评测悄悄失去意义。测试通过项目根路径导入独立benchmark包，用tmp_path写临时JSON，不使用真实provider配置。

## 核心断言

| 范围 | 为什么需要 |
| --- | --- |
| 29例、12类、唯一ID、task_v1 | 防止覆盖范围缩水或悄悄换成永远通过的判分器。 |
| 多次load产生独立对象 | 一个测试改期望不能污染下一次执行。 |
| 文档注入原文保留 | 不把不可信指令预先删除，安全案例才能测试实际边界。 |
| 未知字段/类别/工具/角色/grader/profiles | 结构错误必须显式失败。 |
| setting密钥、超大预算、非法终态 | 不允许案例篡改模型配置或放大执行范围。 |
| 负数记录数量、诊断偏好、无效证据key、倒置上下界 | 防止判分条件本身无意义。 |
| 故障与loop仅contract | 工程强制行为不能冒充provider能力。 |
| hash碰撞原词及无respond | synthetic3/synthetic68回归必须实际检索，不能写固定答复自证。 |
| 零证据案例要有回答约束 | 即使检索空也不能无条件接受任何自然语言结论。 |

write_cases只是测试夹具写入函数，不生成正式数据集。所有非法结构使用pytest.raises(ValueError)，包含Pydantic校验错误。

## 验证方法与限制

从backend运行pytest tests/unit/test_benchmark_cases.py。测试只证明语料结构与防错规则，不能证明provider理解任务或所有案例通过；具体工程执行还需[runner集成测试](../integration/test_benchmark_runner.py.md)。

“execution_plan没有expected_state键”的静态断言只是初步隔离检查。真正的oracle不影响决策证明位于集成测试：同一执行计划更换错误oracle后实际状态不变、分数失败。

