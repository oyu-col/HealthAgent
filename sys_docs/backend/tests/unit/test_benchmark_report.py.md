- 对应源码：`backend/tests/unit/test_benchmark_report.py`
- 核对日期：2026-10-11
- 阅读源码：[test_benchmark_report.py](../../../../backend/tests/unit/test_benchmark_report.py)
- 所属目录：[目录说明](README.md)

# 统计分母与实验可比性单元测试

## 定位与夹具

测试针对[report.py](../../../benchmark/report.py.md)的summarize、markdown和compare。trace、result、report辅助函数构造明确的合成事件、状态和manifest，便于逐项改变协议而检查拒绝行为。它不运行模型或数据库。

## 真实事件与未知值

tool_execution只能读取event字段等于tool.finished的事件：同名type字段、tool.started和model.finished均不能混入工具成功率。tool_calls与agent_steps使用Trace计数而非工具计划长度。

空样本、无适用工具或无Trace的分母应为0、值为None；无Trace的token usage不能因为all([])为真而标完整。部分Trace缺失时已知usage可保留，但完整性为False；未完整捕获的工具/步骤样本不能当零加入均值。

## 失败保留与恢复解释

harness_error行仍进入任务成功率与分类分母，并在Markdown出现失败检查。故障恢复必须实际fault_triggered；仅配置recovery_eligible但未触发的行不进入恢复分母。刻意loop_detection与普通任务的unexpected_loop分别计算。

## 比较器反例

测试分别改变mode、案例/grader/协议/设置指纹、选择集、重复次数、seed、schema_version、Python、依赖，要求拒绝。不完整baseline或candidate同样拒绝。

两次重复中一例改善、一例回退但整体成功率不变时，结果必须按(case_id, repeat)分别列出，不把平均值相同说成无变化。双方都重复样本、都缺同一声明样本、含未声明样本或同时缺某指纹，也不能因此变为“可比较”。

## 验证与边界

从backend运行pytest tests/unit/test_benchmark_report.py。测试评估统计协议正确性，不校验远端模型版本、统计显著性或报告的密码学真实性。读取结果时还必须查看runner生成的真实Trace与失败证据。

