# schemas.py：健康输入与统一工具结果

- 对应源码：`backend/app/domain/schemas.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/domain/schemas.py) · [目录说明](README.md)

## 职责与设计

集中定义跨 API、工具、业务服务使用的结构化输入。DomainModel 设置 extra=forbid、字符串去首尾空白、allow_inf_nan=False：未知字段、NaN 和无限值不能悄悄进入数据库。它不存储用户身份，也不负责把 Pydantic 异常映射为 HTTP 响应；那由 API / Agent 中间件处理。

## 类型和关键校验

| 类型 | 字段及当前限制 |
| --- | --- |
| MetricType / MetricUnit | weight/kg、heart_rate/bpm、sleep_duration/hours、steps/count |
| MetricInput | value 非负；体重和心率必须大于零；步数必须整数；睡眠不超过 24 小时；measured_at 为可选 AwareDatetime |
| NutritionInfo | calories、protein_g、fat_g、carbohydrate_g 均可空，给值时非负 |
| DietInput | food_name、amount 为 1–200 字符；meal_type 为 breakfast/lunch/dinner/snack；可选 timestamp、nutrition_info |
| ExerciseInput | exercise_type 为 1–200 字符；duration 为分钟，0 < duration ≤ 1440；distance 公里和 calories kcal 可空且非负 |
| QueryInput | 带时区 start/end，可选 metric_type；limit 默认 100、范围 1–200；start 不得晚于 end |

compatible_unit() 负责指标种类与单位配对及额外数值约束；ordered() 检查查询时间顺序。未填写时间的默认值由 [HealthService](../services/health.py.md) 在写入时补齐，schema 本身不调用时钟。

## ToolResult 与 UTC 输出

ToolResult 包含 success、data、error_code、error_message、retryable。ok(data) 创建成功结果；fail(code,message,retryable=False) 创建失败结果。data 为 Any，当前没有针对每类工具的泛型输出校验，也没有强制“success 与 error_code 必须互斥”的额外验证器；调用方应使用两个工厂保持一致。

iso_utc() 把传入 datetime 直接 replace(tzinfo=UTC)，再输出 ISO8601/Z。它适用于 Repository 中已经标准化成“无时区 UTC”的数据库值，**不是任意带时区时间的通用时区转换函数**；外部时间应先经 utc_naive()。

## 调用与变更注意

[健康工具](../tools/health.py.md) 将这些模型公开成工具参数 schema；[健康服务](../services/health.py.md) 使用 model_validate 和稳定 JSON 摘要；[Repository](../persistence/health_repository.py.md) 只接收校验后的值。更改默认值或序列化形式会改变幂等 payload_hash，应评估旧请求回放兼容性。

[测试](../../tests/integration/test_health_tools.py.md) 明确覆盖负值、错误单位、NaN、分数步数、无时区时间；[UI 测试](../../tests/integration/test_ui_api.py.md) 覆盖额外字段、错误记录种类和查询边界。本页依据源码说明，未重新运行测试。
