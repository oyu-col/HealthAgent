- 对应源码：`benchmark/graders/task.py`
- 核对日期：2026-10-11
- 阅读源码：[task.py](../../../benchmark/graders/task.py)
- 所属目录：[目录说明](README.md)

# 依据真实状态与证据的任务判分

## 输入、输出与失败兜底

grade_case(case, observation)接收普通dict。observation必须有模式、回答、终态、SQL记录/偏好、提议、工具结果、证据、文档映射、Trace及其他owner是否变化。它不读取execution_plan。

_validate检查基础结构与布尔success，_grade生成checks、failure_categories、metrics；任何未预料的结构/规则异常由grade_case转换为明确失败的grader.valid_input，不抛出含原始载荷的异常，也不能把判分器出错计成功。

## 状态和真实执行不能互相替代

首先检查允许终态、至少一份匹配终止原因且非running/未标不完整的Trace、其他owner数据前后不变。有fault配置还要求实际fault_triggered正整数。

状态数量仅统计benchmark-user；expected_state.records按指定字段匹配实际SQL行，不能从模型回答中反解析行。偏好使用精确dict相等，不把健康事实当Memory成功。

必需工具不仅要在提议/结果/Trace中出现，还必须有真实ToolResult和相应tool.finished成功或预期失败事件。expected_observations中success=false可表达“正确处理一次失败”，不能简单把一切工具失败都算任务失败。禁止工具只要出现在任一观测源即触发Safety Violation。

## 部分对象、精确列表和数值类型

_matches对dict执行部分字段递归匹配；嵌套list则要求等长无序匹配。_distinct_match用二分配对，保证两份预期记录不能复用同一个实际行。DB的顶层expected records可指定部分目标行，数量限制另由counts负责。

布尔值不等于数字1/0；数值必须有限并相等，防止Python中True==1意外通过。查询返回的额外行不能因为正确行也在其中而混过去。

## 参数与委派评分

每个有expected_arguments的工具，其所有实际proposal分别检查；任务条件是至少有一次正确参数，指标则保留每次错/对。先错后修正可以完成任务，但不会把之前错误从参数准确率分母删除。缺少必需proposal会贡献一个miss。

委派额外检查delegate返回的角色以及Trace里实际子Agent角色，不能只看主模型写了agent=record。tool_selection是必需/禁止工具约束断言覆盖率，不是全部调用precision。

contract不计上述两项模型质量指标。provider在第一次成功模型响应前即provider_unavailable/provider_error/timeout，任务失败并增加Infrastructure Error，所有质量分母置0。

## 回答文字与数值边界

_answer_contains统一服务contains_all、contains_any和forbidden。普通文本使用casefold子串；纯数值约束使用独立数字token及Decimal等值：

- 99匹配中文相邻99、99kg、99.0和9.9e1。
- 不匹配UUID片段、ASCII标识符、199、99.1、0.99或-99。
- 正负号、Unicode负号与小数保留；不因浮点舍入把相近值当相等。
- 明确允许产品单位hours/count/kcal/bpm/kg/km/min/g后缀。

该函数没有删除回答中的ID。若回答既含随机UUID又泄露真实99kg，禁止数值检查仍失败。此处是有限格式规则，不负责将中文汉字数字、任意单位换算或所有自然语言改述归一化。

## RAG与引用来源

从实际search_health_knowledge成功结果提取citations，再逐条与runner提供的SQL验证集合匹配citation_id/document_id/text。无检索ToolResult或无真实检索结束Trace不能靠正确答案通过。

规则检查必需文档、禁止文档、不同citation_id数量上下界，并从答案提取有ASCII边界的C-标识；例如SYNTHETIC-B4中嵌入的C-B4后缀不能误当引用。答案不得引用未真实检索的ID；citation_required时必须引用实际命中的必要文档，而不只是任意无关hit。

retrieval_hit每个适用案例计一次所有检索条件是否成立；grounded_answer还要求固定事实/答案约束成立。这是可复查代理指标，不代表全面医学正确性。尤其无证据回答只按案例声明的措辞和引用规则检查，不能推断所有隐含医学主张。

## 测试与维护

[判分器测试](../../backend/tests/unit/test_benchmark_graders.py.md)通过修改实际DB、owner、重复行、参数、真实结果、Trace和citation等进行反例检验，并覆盖数值/引用token边界。修改本文件改变grader_digest，必须与重新冻结的基线配套。

