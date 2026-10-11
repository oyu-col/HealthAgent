- 对应源码：`benchmark/observation.py`
- 核对日期：2026-10-11
- 阅读源码：[observation.py](../../benchmark/observation.py)
- 所属目录：[目录说明](README.md)

# 内存观察、数据库快照与引用证据核验

## 与生产Trace的区别

生产Trace只保存白名单执行元数据；本模块在合成benchmark期间，为独立判分暂时保留工具提议和结果原文。Capture不是生产日志替代品，runner只把经过选择的计数、检查和脱敏Trace写入报告，原始observation随当前运行释放。

## Capture如何采集

on_chat_model_start以run_id保存可信health_agent_name；on_llm_end从实际返回的AIMessage.tool_calls提取name、args和角色，作为参数准确率依据。它不从execution_plan反推出模型“应该调用什么”。

on_tool_start保存工具与角色身份；on_tool_end把ToolMessage、JSON文本或dict交给add。add仅接收带布尔success的统一结果信封，保留真实result，对完全相同entry去重。runner还从Lead checkpoint补读ToolMessage，以覆盖某些框架边界归一化后的最终结果。

run_inline=True使采集跟随回调执行；raise_error=True意味着采集异常不会悄悄变成一个无证据的成功样本。

## 模型错误的脱敏信息

on_llm_error最多沿__cause__追踪5层，仅保存异常类型名和整数errno/status_code。它不存异常消息、请求头、provider URL、prompt或响应原文。该受限列表可帮助区分连接失败与HTTP拒绝，不能据此猜测未观测的内部重试。

## snapshot：直接读取SQL

OWNER固定benchmark-user。TABLES包含HealthMetric、DietRecord、ExerciseRecord；snapshot按主键顺序读取全部owner行，保留user_id供隔离核验，datetime用iso_utc转字符串。偏好只读取当前OWNER并转成key→value。

读取全部owner的健康记录仅发生于临时合成环境，用于比较其他用户前后快照，不能把这段跨owner读取移入生产API。

## 证据发现与独立验证

evidence递归扫描实际ToolResult，包括委派报告嵌套observations，收集同时具备citation_id、document_id和text的条目，按citation_id去重。

verified_evidence再以C-后缀查真实KnowledgeChunk，并关联DocumentIndex和HealthDocument。它要求：

- 索引为public，或index.user_id等于OWNER。
- 文档处于indexed。
- 返回document_id和text与真实行一致。
- page与实际chunk相同，index_version与实际索引相同。

任何伪造或不满足条件的条目都不进入验证结果。grader还核对实际检索结果与这些SQL证据，避免只凭模型答案里出现C-ID即得分。

## 限制与测试

这里校验的是来源真实性和当前可见范围，不评判正文医学真实性，也不赋予文档中的指令权限。文档filename/source等可读字段不是完整数字签名；判分依靠实际chunk对应关系与必要事实约束。

[集成测试](../backend/tests/integration/test_benchmark_runner.py.md)实际索引文档，然后只篡改工具返回正文，确认SQL核验拒绝该引用。计数应使用生产Trace，不能使用去重后的observations数量代替物理工具尝试数。

