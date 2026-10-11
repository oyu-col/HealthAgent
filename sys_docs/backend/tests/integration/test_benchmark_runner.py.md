- 对应源码：`backend/tests/integration/test_benchmark_runner.py`
- 核对日期：2026-10-11
- 阅读源码：[test_benchmark_runner.py](../../../../backend/tests/integration/test_benchmark_runner.py)
- 所属目录：[目录说明](README.md)

# 评测执行器的真实数据与独立判分集成测试

## 运行路径

本文件导入benchmark.runner.run_case和schema.load_cases，以contract模型经过实际FastAPI lifespan、ASGI请求、LangGraph、SQLite与checkpoint。离线模型只控制工具决策，数据读写和证据验证实际发生。pytest沿用conftest的隔离配置和禁网措施。

## 五类验证

1. **实际查询与oracle隔离**：运行query_owner_weight，断言当前用户两条指标、真实两次模型调用；随后仅将expected数量改成0并加入ORACLE_LEAK_MARKER。第二轮实际记录数与调用数不变，而判分失败，证明期望条件不能反向驱动模型回答或环境。
2. **相同请求重放**：选interaction=replay案例，断言两次HTTP尝试、两份Trace，cached Trace的model_calls和tool_calls都为0。它验证重放不虚构模型工作量，也不重复真实写入。
3. **实际索引RAG**：运行一个有min_citations的RAG案例，所需文档key必须出现在实际检索到的文档集合。
4. **伪造正文拒绝**：创建真实应用并索引合成文档；第一次verified_evidence有结果，只修改返回正文后必须为空，不能让工具自称的citation通过SQL核验。
5. **临时数据库回收**：运行前后比较backend下.benchmark-*目录集合，正常案例退出后不应遗留新的临时目录。

## 设计目的与限制

这些断言连接“独立判分理论”与真实产品实现：单元测试人工编写的观测可以是自洽的，但只有这里实际跨层执行才能证明runner没有用expected直接填充状态。

本文件仍不调用真实provider，不检验医学问答质量；没有覆盖所有CLI配置失败、全部故障组合或真实进程崩溃。对应补充来源为[案例结构测试](../unit/test_benchmark_cases.py.md)、[grader反例测试](../unit/test_benchmark_graders.py.md)、[报告测试](../unit/test_benchmark_report.py.md)及各可靠性集成测试。

## 执行

从backend运行pytest tests/integration/test_benchmark_runner.py。测试会创建受控临时目录并在应用/模型/数据库生命周期结束后清理；不使用生产data目录，也不将本地.env凭据发送出去。

