- 对应源码：`docs/phase-11-12-validation.json`
- 核对日期：2026-10-11
- 阅读源码：[phase-11-12-validation.json](../../docs/phase-11-12-validation.json)
- 所属目录：[目录说明](README.md)

# Phase 11–12 机器可读验收事实与限制

## 顶层状态的含义

recorded_at为2026-10-11，phases为11和12。status明确为engineering_complete_online_evaluation_blocked：工程实现和本次离线闭环已完成，完整在线模型评测受连接问题阻塞。不能截取部分passed字段后把总状态描述成所有线上能力通过。

git_metadata_available=false，版本识别依靠源码、案例、grader、protocol、设置及锁文件SHA-256。user_confirmed_keep_provider_failure记录已确认保留真实连接失败；不是未来自动重试或更换服务的授权配置。

## 分区与实际验收数据

| 分区 | 保存内容与实际结果 |
| --- | --- |
| backend | 全量离线pytest：352 passed、1 skipped、43.71秒，命令使用独立basetemp=.pytest-tmp-phase12。 |
| lint | backend/app、scripts、tests及benchmark手写源码，排除runs；98个Python文件Ruff检查与格式检查通过。 |
| frontend | 33个单元测试、10个浏览器测试（8.4秒），lint/typecheck/build通过；只同步healthz phase夹具，production_ui_changed=false。 |
| smoke | 实际API与真实浏览器UI通过，mocked_api=false，但model_mode=fake；验证服务/数据库/索引/会话链路，不等同在线模型质量。 |
| benchmark | 29例、12类、contract重复2次，真实baseline/candidate摘要、指纹及配对列表。 |
| provider | 3次实际单案例模型连接尝试，成功模型响应0，未跑完整22例、未做在线前后对比。 |
| documentation | 最终覆盖报告与新/历史源码快照位置；具体链接验收数字另存coverage报告，避免本文件与其互相循环更新。 |
| environment | Python3.12.10、backend锁文件SHA-256及四个核心包版本。 |
| limitations | 尚未解决问题及协议可解释范围。 |

backend跳过的是需要--run-live的既有live smoke；这不否认本阶段通过独立Benchmark执行了3次真实连接请求，也不能把跳过的一项视作已通过。

## Smoke能证明什么

checks列出healthz、OpenAPI、chat、Trace header、thread历史、Memory提取/删除、document index、TCP SSE、持久Trace、真实浏览器交互及服务优雅退出。model_mode=fake意味着网页到后端的连接、生命周期和业务数据流程真实，但模型答案来自演示路径。

所以real_browser_ui=true与“真实provider未完成”不矛盾：前者是浏览器/HTTP/UI链路验收，后者是外部模型响应与领域能力验证。

## 正式离线比较

benchmark.baseline和candidate直接保留已审阅报告摘要，源结果路径分别指向[基线说明](../benchmark/results/baseline-contract.json.md)、[候选说明](../benchmark/results/candidate-contract.json.md)，comparison_report对应[比较说明](../benchmark/results/comparison-contract.json.md)。

成功率50/58到52/58，提升3.45个百分点；improved仅为rag_hash_collision_no_overlap两次重复，regressed为空，unchanged_failures为三种案例各两次。comparable=true只在相同冻结协议与样本下成立。

retrieval_hit/grounded_answer从10/14到12/14；工具终态覆盖仍64/68，恢复率仍2/4。candidate工具/步骤分布的n为54，基线为58，因为4份缺结束事件的Trace被正确标不完整；任务成功率仍以全部58例计分。耗时下降只记录为实测波动，不作性能提升结论。

## 在线限制与旧试跑

provider.status=provider_unavailable；safe_diagnostic记录TLS握手被SSLEOFError中断及更早TCP探测超时。没有凭据或endpoint写入记录。latest_report只有一例一次请求，其他尝试通过聚合字段计数，不能把最新报告误认为完整22例。

provider连接报告使用较早grader指纹，且模式/配置/选例与contract不同，不参加前后比较。正式v3之前纠正数值/引用oracle的v1/v2试跑也被排除；本文件不是跨评分器拼接的提高幅度。

## 不应被隐藏的限制

弱词重合误召回仍存在；工具timeout/cancel的真实finished缺口未补造，只正确声明capture_complete=false。规则事实/citation是合成代理，不是临床验证。

manifest只记录四个核心依赖版本，未覆盖完整运行依赖图；compare信任生成的summary，本轮另经逐行核对。某些provider重复结束回调可能重复记录proposal；本次contract选择/参数指标为N/A，后续在线评测需补充这一边界。

这份验收JSON应保持阶段历史事实，不用后来的成功实验覆盖当前限制；新增实验应另建报告和对应解释。

