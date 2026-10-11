- 对应源码：`benchmark/environment.py`
- 核对日期：2026-10-11
- 阅读源码：[environment.py](../../benchmark/environment.py)
- 所属目录：[目录说明](README.md)

# 合成环境准备和局部故障注入

## seed：通过实际业务层建立夹具

seed(app, case)读取initial_environment，而不是expected_state。records逐条进入app.state.health.add，使用随机操作key；Service仍负责业务模型、UTC转换、幂等收据及Repository事务。若ToolResult.success不成立，环境初始化直接失败。

documents使用knowledge.ingest真实解析、向量化并保存chunk，必须达到indexed；返回的documents字典把稳定逻辑key映射为随机数据库document_id。preferences通过MemoryService.update设置。种子建立在故障注入之前，不让初始化失败伪装成任务失败。

## inject_fault：仅改变当前app实例

上下文管理器将target映射到当前应用的health.query/health.add、knowledge.search或traces.finish，保存原方法，再替换为异步wrapped。finally无论正常结束或异常均恢复方法，不修改类或生产配置。

counter同时记录符合record_kind筛选的attempts，以及真正命中注入的triggered次数。runner将triggered交给grader，防止模型根本没调用目标工具却把故障恢复计成功。

| kind | 行为 |
| --- | --- |
| transient_once | 首次抛出合成ConnectionError，后续调用转原方法，观察框架有界读取重试。 |
| permanent | 每次目标调用都抛出合成RuntimeError。 |
| timeout_once | 首次睡眠超过工具超时；若是add，先真实写入再睡眠，制造“已提交但响应未知”。 |
| finish_once | 首次Trace.finish抛出RuntimeError，后续恢复，用于收尾错误研究。 |

## 写后超时的重要含义

timeout_once在add上不能简单理解为“没有写成功”。原Service已经执行并可能提交，调用方随后因超时只能得到write_outcome_unknown。正确行为是查询现有记录核对，而不是自动重放写操作。当前恢复案例以DB恰好一条记录与真实查询结果共同判分。

## 限制与验证

这是受控故障环境，不模拟操作系统崩溃、跨机器网络或多worker竞争。故障记录kind筛选适用于当前Service位置参数接口；签名变化时必须同步。睡眠故障依赖外层真实工具timeout取消，工具超时预算不能随意拉高而声称保护有效。

[runner集成测试](../backend/tests/integration/test_benchmark_runner.py.md)验证真实夹具和资源回收；故障的具体正确性还由后端reliability测试与案例Trace检查负责。报告中的fault_triggered比计划里“配置了fault”更有证明力。

