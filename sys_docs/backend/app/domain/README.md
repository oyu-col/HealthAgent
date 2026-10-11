# domain：业务数据契约

- 对应目录：`backend/app/domain/`
- 核对日期：2026-10-04
- 源码：[目录](../../../../backend/app/domain/)；上级：[app 说明](../README.md)

## 设计目的

这个目录用 Pydantic 描述“合法的健康业务输入”和统一工具结果，使 HTTP 表单与 Agent 工具复用一套校验。它不负责认证、SQL、模型调用或自动诊断。身份授权属于 API 和可信 RunContext，不能在业务 record 中增加可由用户自行填写的 user_id 作为授权依据。

## 文件与调用关系

- [schemas.py](schemas.py.md)：指标、饮食、运动、查询、ToolResult 及 UTC 输出函数。
- [__init__.py](__init__.py.md)：包说明，无运行逻辑。

调用链为 API / LangChain 工具参数 → DomainModel 校验 → Service → Repository。返回链为 Repository 普通字典 → ToolResult → HTTP 或模型工具观察。Service 会再次校验写入对象，避免直接调用 Service 时绕过输入契约。

## 关键约束与实际边界

时间输入必须包含时区，Service 转换为 UTC 后以无时区 datetime 存储；输出再恢复 Z 标记。单位是固定集合，不自动做磅转千克。饮食营养和运动热量允许未知，不由 schema 估算。QueryInput.limit 是列表上限，不能用于替代趋势全范围统计。当前字段只是应用约束，不是临床参考范围。

对应行为见 [健康工具集成测试](../../tests/integration/test_health_tools.py.md) 与 [UI API 集成测试](../../tests/integration/test_ui_api.py.md)。扩展指标需同时修改 schema、前端选项、工具描述、统计逻辑和兼容性测试；已有 SQLite 表结构变动还需要迁移方案。
