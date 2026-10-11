- 对应源码：`backend/app/api/records.py`
- 核对日期：2026-10-04
- 阅读源码：[records.py](../../../../backend/app/api/records.py)
- 所属目录：[目录说明](README.md)

# 健康记录表单的直接业务接口

## 定位与设计目的

允许前端表单直接查询/新增指标、饮食、运动记录，复用 Agent 工具使用的 HealthService。fake 模型不理解工具调用时，表单仍可真实入库。

## 类型、输入与输出

RecordKind 只允许 metric、diet、exercise。GET 接收 QueryInput 查询参数，返回统一 ToolResult。metric_type 只能用于 metric 路径，其他路径携带它立即返回 invalid_request/422。
POST 的 body 是 MetricWrite、DietWrite、ExerciseWrite 三者之一：每种都要求嵌套 record 与必填 request_id UUID；record 使用对应领域模型。WRITE_SCHEMAS 再验证 body 的具体模型与 URL kind 一致，防止“饮食路径+指标载荷”被联合类型解析接受。

## 实际执行链

GET → health.query(kind, user_id, query)。
POST → 校验 body 与 kind → health.add(kind, user_id, record, 幂等键) → 成功返回 ToolResult；失败将结果中的 error_code/error_message 转成 AgentError，HTTP 409。

## 幂等、权限与错误边界

幂等键固定为 `http-record:<request_id>`，与图内工具写入回执的命名空间隔离。相同请求内容沿用原 ID 可去重，改变内容复用 ID 会冲突；实际比较和原子事务由服务/Repository 实施。
身份只从服务端依赖传入，模型和 UI 共用同一 owner 隔离规则。读取结果可能用 HTTP 200 承载 success=false，因此前端必须检查 ToolResult；POST 此模块则将业务失败提升为 HTTP 409。不是所有接口都采用相同的错误包装方式。

## 验证与修改注意

UI API 测试覆盖三类记录、查询筛选、严格参数、按用户隔离和同请求冲突。修改 schema 必须同步前端输入单位/嵌套结构；新增删除或覆盖能力不能仅增加路由，还需设计确认与领域事务约束。

## 相关源码说明

- [backend/app/domain/schemas.py](../domain/schemas.py.md)
- [backend/app/services/health.py](../services/health.py.md)
- [backend/tests/integration/test_ui_api.py](../../tests/integration/test_ui_api.py.md)
- [frontend/src/components/Records.tsx](../../../frontend/src/components/Records.tsx.md)

