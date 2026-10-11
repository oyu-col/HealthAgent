- 对应源码：`benchmark/results/provider-connection.json`
- 核对日期：2026-10-11
- 阅读源码：[provider-connection.json](../../../benchmark/results/provider-connection.json)
- 所属目录：[目录说明](README.md)

# 真实provider单次连接失败的诊断证据

## 报告范围

本文件使用manifest、summary、results运行报告结构，创建于2026-10-11 04:16:56 UTC，即北京时间12:16:56。mode=provider，但selected_cases只有query_owner_weight，repeats=1；不是22个provider适用案例的完整评测。

profile_excluded_cases列出7个仅限contract工程案例；其他未选provider案例也没有运行，不能把缺席解释为通过。completed=true只说明这次选定的一条运行已收尾，不表示模型成功响应。

## 实际失败信息

任务0/1通过，termination=provider_unavailable。model_errors保存的异常类型链为OpenAIConnectionError → APIConnectionError → ConnectError → ConnectError；没有记录异常原文、服务URL或密钥。该证据支持“连接调用失败”，不能仅靠类型链断定具体网络、服务或权限原因。

Trace显示一次模型调用开始、没有成功模型输出、工具调用为0。实际Agent执行耗时约5114.538ms，整案例约7169.446ms；token usage=null且不完整。

## 如何理解质量指标

tool_selection、tool_arguments、retrieval_hit、grounded_answer等分母为0，显示N/A。基础设施尚未给出模型决策时，不能靠“禁止工具没有被调用”得到虚假高分，也不能把无调用简单当成模型选择差。

结果仍保留缺工具、缺参数、缺观测、缺答案的失败检查，并增加Infrastructure Error。这里其他失败分类是中断造成的后果；不能用它们推断该模型推理能力、医学知识或工具熟练度。

## 与正式比较的区别

该文件的grader_digest以bc599660开头，contract两轮正式报告以9b5651f8开头；模式、配置、选择集和重复次数也不同。所以它只作为当时真实provider尝试失败的证据，不属于[comparison-contract](comparison-contract.json.md)的baseline/candidate配对。

连接修复后需在当前冻结协议下重新执行provider基线和同模式候选；不能把这份0/1与离线52/58做提升比较，也不能用fake替代真实请求后沿用provider标签。

