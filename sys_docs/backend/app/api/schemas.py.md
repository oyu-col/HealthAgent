- 对应源码：`backend/app/api/schemas.py`
- 核对日期：2026-10-11
- 阅读源码：[schemas.py](../../../../backend/app/api/schemas.py)
- 所属目录：[目录说明](README.md)

# HTTP 对话协议与响应模型

## 定位与设计目的

集中定义 HTTP 层的 Pydantic 协议，隔离客户端可输入的字段与服务端产生的执行元数据。它不包含健康事实的指标/饮食/运动校验，那些属于领域 schemas。

## 关键类型和输入输出

| 类型 | 真实字段与约束 |
| --- | --- |
| `ChatRequest` | message 必须是严格字符串，去除首尾空白后至少 1 字符，最大值受 `HARD_INPUT_LIMIT` 限制；thread_id、request_id 为可选 UUID；拒绝额外字段。 |
| `ResumeRequest` | 必须提供 request_id UUID，拒绝额外字段；恢复请求不再次携带 message。 |
| `ChatResponse` | answer、trace_id、run_id、thread_id、request_id、model_mode、memory_updates；termination_reason 只能为 completed。 |
| `HealthResponse` | status 固定 ok，phase 使用 Literal[12] 且默认值为 12，并返回模型模式。 |
| `ThreadMetadata` | 会话创建时间、活跃请求、标题、idle/running/failed/interrupted 状态、can_resume 与 pending。 |
| `ThreadResponse` | 在元数据基础上增加 messages，消息角色只允许 user 或 assistant，content 为字符串或列表。 |
| `ErrorDetail` / `ErrorResponse` | error 包裹固定错误码、可公开消息、trace_id 和可选恢复标识。 |

## 调用链与边界

FastAPI 根据这些模型完成请求校验和响应序列化。API 层还会使用运行配置的 `max_input_chars` 检查消息长度，因此硬限制通过不代表当前配置也允许。user_id 不在请求模型中：身份必须来自 auth 依赖，客户端增加它会被拒绝。
`pending` 描述图状态，`can_resume` 是业务服务综合回执与 checkpoint 得出的恢复能力；前端不应只根据 pending 判断能否恢复。响应中 completed 是终态承诺，不能拿半截模型输出套用此类型。

`HealthResponse.phase` 是当前应用交付阶段的常量标识，不是一次运行的阶段进度，也不表示实时执行过 Benchmark、真实模型已连通或医学质量已验证。健康探针只返回状态与配置中的 model_mode；Phase 11/12 的评测执行与报告属于独立 benchmark 工具链。

## 验证与修改注意

API 集成测试验证空值、非字符串、越界长度、伪造身份和非法 UUID 不进入模型；UI 接口测试覆盖线程元数据。增删字段时同步前端类型、SSE completed 数据和 OpenAPI 契约。

## 相关源码说明

- [backend/app/config.py](../config.py.md)
- [backend/app/domain/schemas.py](../domain/schemas.py.md)
- [backend/tests/integration/test_api.py](../../tests/integration/test_api.py.md)
- [frontend/src/lib/types.ts](../../../frontend/src/lib/types.ts.md)

