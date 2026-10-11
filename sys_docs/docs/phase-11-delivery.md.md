- 对应源码：`docs/phase-11-delivery.md`
- 核对日期：2026-10-11
- 阅读源码：[phase-11-delivery.md](../../docs/phase-11-delivery.md)
- 所属目录：[目录说明](README.md)

# Phase 11 领域基准的实现与验收说明

## 源文件用途和章节结构

该交付文件遵循项目规定的七节：Completed、Files Changed、Design、DeerFlow Reference、Tests、Known Issues、Next Phase。它说明已经实现哪些评测能力、代码位于何处、证据从哪里来以及当前仍未验证什么。

文件开头明确“工程实现完成，在线模型能力验收因连接故障未完成”。profiles适用22个provider案例是框架支持范围，不应误读为已实际完成22例真实模型评测。

## 已实现的评测链

29个版本化合成案例覆盖12类任务。runner使用实际应用lifespan、健康Service/SQL、官方checkpointer与ASGI请求；contract固定决策，provider只拿用户问题、工具schema和真实观测。fault仅作用当前临时应用，退出恢复。

grader将提议、工具结果和DB状态分开。查询列表要求等大小多重集合，写入检查真实值、时间和数量；RAG从SQL核验chunk与可见owner。参数按每次真实proposal计分，先错后对不会抹掉历史错误。数字及引用token边界防止UUID/编号误报。

manifest记录案例、grader、protocol、app与设置指纹；compare拒绝不完整、样本异常和不同协议实验。这些是可复现性防错措施，不是完整依赖锁定或防篡改数字签名。

## 指标应怎样解读

工具选择率是必需/禁止约束覆盖率，不是每次调用precision。contract的选择与参数分母0；连接失败且模型尚无成功响应时，任务仍失败，质量指标分母归0。

工具执行率只包含已观测finished的尝试，另有finished/started覆盖；调用/步骤均值只采用完整Trace。usage缺失是null。检索和groundedness是固定事实/citation代理，不能替代医学事实评审。

## 原文件记录的验证与限制

源文件记录schema23、grader128、report26、runner集成5项通过，以及全后端352 passed、1 skipped和98个手写Python文件的Ruff/格式检查。这些是该阶段实际验证记录，不是本文重新执行后的结果；最终状态应以机器可读验收为准。

真实provider总共进行了3次单案例连接尝试，没有得到模型回答；审阅归档只保留最新脱敏连接报告。本次不把连接失败解释为模型推理差，也不把contract通过解释为线上能力通过。

Known Issues还指出：仅记录四个核心依赖版本，无法保证任意跨环境复现；compare未重算手工篡改的summary；某些provider补发on_llm_end可能重复记录proposal。这些限制没有在冻结实验中通过临时改协议隐藏。

## 参考与阶段关系

DeerFlow仅作为任务状态核验和重复统计的只读代码参考，未调用相关Skill、未复制Agent执行器或引入运行依赖。两份参考文件及SHA-256见[参考记录说明](phase-11-12-deerflow-reference.json.md)。

Phase12已完成本次离线优化闭环；服务恢复后仍需另建真实provider基线。具体可比数据见[结果目录](../benchmark/results/README.md)，不能沿用本次连接失败作为模型能力基线。

