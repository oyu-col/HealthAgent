- 对应源码：`backend/app/api/traces.py`
- 核对日期：2026-10-04
- 阅读源码：[traces.py](../../../../backend/app/api/traces.py)
- 所属目录：[目录说明](README.md)

# 执行 Trace 查询接口

## 定位与接口

提供只读的 /api/traces 接口，使前端能查看实际执行元数据，不向浏览器暴露 Runtime 或 checkpoint 原始内容。
GET /api/traces 接受可选 thread_id UUID、limit（默认 20，范围 1–100）、offset（默认 0，范围 0–10000），调用 traces.list(user_id, ...) 后返回 traces、limit、offset。
GET /api/traces/{trace_id} 对 trace_id 做 UUID 校验后调用 traces.get(user_id, trace_id)。

## 数据流与权限

调用者通常为前端 TraceDialog；request.app.state.traces 是生命周期装配的持久化查询对象。路由不收集事件，也不负责对模型输出做脱敏。安全性依赖记录器写入白名单和 Repository 查询时强制 user_id 过滤两层配合。
传 thread_id 只是过滤，不能代替身份验证。路径 ID 可被猜到也不授权读取；不存在或不可见记录由下游返回对应安全错误。

## 状态和返回解释

列表是分页元数据，详情附执行事件。未知 token usage、未完成 Trace、裁剪事件等字段应按存储内容原样理解，不能在前端把 null 自动当 0。这里没有导出健康原文、删除 Trace 或开启外部追踪的接口。

## 验证与修改注意

test_observability 验证 Trace 持久化、隔离、脱敏和异常分支；test_trace_recorder 验证事件计数、去重与保留策略。扩大查询范围时保持有界 limit/offset，不要直接开放数据库整表下载。

## 相关源码说明

- [backend/app/persistence/trace_repository.py](../persistence/trace_repository.py.md)
- [backend/app/observability/recorder.py](../observability/recorder.py.md)
- [backend/tests/integration/test_observability.py](../../tests/integration/test_observability.py.md)
- [backend/tests/unit/test_trace_recorder.py](../../tests/unit/test_trace_recorder.py.md)
- [frontend/src/components/TraceDialog.tsx](../../../frontend/src/components/TraceDialog.tsx.md)

