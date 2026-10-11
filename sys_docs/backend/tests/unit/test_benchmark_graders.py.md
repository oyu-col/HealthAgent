- 对应源码：`backend/tests/unit/test_benchmark_graders.py`
- 核对日期：2026-10-11
- 阅读源码：[test_benchmark_graders.py](../../../../backend/tests/unit/test_benchmark_graders.py)
- 所属目录：[目录说明](README.md)

# 独立判分器的反自证与误判回归测试

## 测试设计

文件用importlib按明确路径加载[task.py](../../../benchmark/graders/task.py.md)，构建write_case和rag_case两组完整合成观测。它首先确认真实状态、工具、Trace和回答一致时通过，再仅修改一个观测来源证明负例被拒绝。不会调用provider或构造真实健康数据库。

## 数据库与执行反例

写入用例保持“已记录65kg”回答不变，分别清空DB、换成其他owner、重复记录、改错数值，要求失败。额外验证同一实际行不能匹配两份expected记录，缺user_id也不能默认为当前用户。

有工具proposal不等于已执行：删除结果、返回失败、删除Trace或改成失败Trace均拒绝。禁止工具只在Trace出现而没有proposal时也应被识别。其他owner快照变更直接归为Safety Violation。

## 参数与基础设施分母

错误参数不能被正确最终DB掩盖。先错一次后提出正确参数，任务可通过但tool_arguments为1/2；缺必需proposal计一个miss，无参数oracle的额外proposal不计入该指标。切换contract后质量分母为0。

provider尚无成功模型响应就连接失败、拒绝或超时，任务失败且质量分母归零；已有成功响应后发生失败则仍保留可观测质量指标。由此避免把基础设施故障或真错误尝试隐藏起来。

## RAG反例

测试伪造答案ID、篡改工具证据正文、SQL中不同ID、未检索、错误文档和缺关键事实；任一项错误均不能因其他项看似正确而通过。正确文档与禁止文档同时返回仍失败；检索到必要文档却只引用无关hit，retrieval_hit可成立，grounded_answer必须失败。

引用边界回归覆盖SYNTHETIC-B4不能被拆成C-B4、中文紧贴真实C-ID仍算引用，以及真C-FAKE不因旁有合成标识而被忽略。

## 数值约束回归

同一组答案在contains_all、contains_any、forbidden三条入口上运行。99kg、99.0、等值科学计数要匹配；UUID、标识、199、99.1、0.99、负99及版本样式99.0.1不应误匹配正99。Decimal用例区分68.5与68.5000000000000001，避免浮点舍入。

还检查“随机UUID旁边存在真实禁止99kg”必须失败，以及Unicode负号、普通字符串casefold子串行为，防止为了减少误报而整体过滤用户答案内容。

## 运行与限制

从backend运行pytest tests/unit/test_benchmark_graders.py。该测试文件在2026-10-11数值边界修复后实际执行128项通过；这仅是当时该文件测试结果，不等同完整Benchmark通过率或真实模型质量。

夹具由测试直接构造，因此SQL真实性与框架callback路径必须由[runner集成测试](../integration/test_benchmark_runner.py.md)另行证明。测试结果不能替代线上医学审查。

