- 对应源码：`benchmark/schema.py`
- 核对日期：2026-10-11
- 阅读源码：[schema.py](../../benchmark/schema.py)
- 所属目录：[目录说明](README.md)

# 案例结构、预算与评测模式的严格校验

## 定位与输入输出

load_cases(path=None)读取指定UTF-8 JSON，默认使用cases/health-v1.json。根对象必须是非空列表；每项经BenchmarkCase校验，转为补齐默认值的全新普通dict，最后检查case_id全局唯一。返回值供runner选择和执行，整个case不能直接交给模型。

## 模型分工

| 模型 | 关键内容 |
| --- | --- |
| StrictModel | extra=forbid；拒绝未知字段和非有限浮点。不是所有字段都开启Pydantic strict类型模式。 |
| SeedRecord / SeedDocument | 指定真实环境种子；记录kind限制metric/diet/exercise，文档含逻辑key、owner、文件名、正文、visibility/source。 |
| Environment | records、documents、preferences；默认空集合。 |
| ToolStep / ResponseStep | contract动作必须是合法工具+args或明确respond文字；不允许额外answer字段。 |
| ExpectedState | 当前用户各表数量、部分记录字段、偏好精确状态。 |
| AnswerConstraints | contains_all、contains_any、forbidden及是否必须引用。 |
| Evidence | 必需/禁止文档key、citation数量上下界。 |
| Fault | 允许query/search/add/trace_finish，以及一次瞬态、永久、一次超时、一次收尾失败。 |
| BenchmarkCase | 组合执行计划、期望、允许终态、交互方式、设置、profiles及固定grader名。 |

## 一致性与模式边界

CATEGORIES固定12类；TOOL_NAMES固定当前10个健康/委派工具；AGENT_NAMES只允许Lead及三个专业角色。工具名存在校验不等于工具参数业务校验，args和record中的业务内容仍需由实际工具/Service验证。

文档key在单案例内唯一；expected_evidence不能指向不存在的key，不能同时要求和禁止同一文档；min_citations不能大于max_citations。同一工具不能既必需又禁止。故障案例及loop_detection必须仅有contract profile，避免把人为强制失败动作当作provider自主行为。

偏好限四个键及产品既有允许值，不能塞入诊断等健康事实。终态必须来自TERMINATIONS枚举；grader固定task_v1。profiles不允许重复，案例ID受小写标识正则限制。

## 有界设置

settings只允许执行预算、超时、重试等白名单字段及memory_enabled/subagents_enabled布尔开关，禁止写model_api_key、data_dir或其他身份/存储配置。整数预算要求整数，数值必须在SETTING_RANGES内；最终仍由运行时Settings执行整体配置约束。

默认值会出现在返回dict中，例如fault=None、expected_evidence.max_citations=None、空preferences。使用者不能以“字典非空”推断本例必然是RAG，需检查具体约束或category。

## 设计目的与测试

schema提前拒绝含糊的评测协议，防止案例字段拼错被静默忽略，或通过改预算/模式让成绩失去可比性。每次load返回新对象，某次测试修改oracle不污染后续案例。

[test_benchmark_cases.py](../backend/tests/unit/test_benchmark_cases.py.md)覆盖29例/12类、ID唯一、未知字段、非法角色/工具/预算、无效证据、空列表、独立对象、contract边界和负检索约束。结构校验本身不证明业务成功。

