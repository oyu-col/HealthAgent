- 对应源码：`backend/app/agent/context.py`
- 核对日期：2026-10-04
- 阅读源码：[context.py](../../../../backend/app/agent/context.py)
- 所属目录：[目录说明](README.md)

# 可信执行上下文 RunContext

## 定位与设计目的

RunContext 通过 LangChain/LangGraph 的公开 context 接口传入图和工具，承载服务端身份、执行关联和共享预算。它与模型可见的工具 schema 分开，模型无法靠指定 user_id 获得别人的权限。

## 关键字段

| 分类 | 字段和含义 |
| --- | --- |
| 身份/时间 | user_id、timezone，由已验证请求和 Settings 决定。 |
| 执行关联 | trace_id、run_id、operation_id、thread_id；operation_id 用作业务请求身份。 |
| 业务结果 | memory_updates 保存已应用偏好变更；tool_observations 保存重复调用指纹计数。 |
| 执行保护 | budget 为共享 ExecutionBudget；agent_name 默认 health_lead_agent。 |
| 子任务 | delegation_depth、delegation_id 标识委派层级和本次子调用。 |
| 可观测性 | event_sink 是可选回调，不参与 repr 和比较。 |

## 创建与数据流

create(settings, trace_id, user_id=None, **kwargs) 生成新的 run UUID；未显式传 operation_id 时沿用 run_id；未传身份时使用配置 local_user_id。预算上限来自 max_tool_calls、max_steps 和 max_delegations。ThreadService 通常显式传入用户、thread、request 标识。
emit(event, **metadata) 只同步调用可选 sink，并补 agent_name，不执行数据库 I/O。安全白名单在 TraceRecorder 端，不能认为任何 metadata 写入后都自动可信。

## 不可变外壳与可变共享成员

数据类使用 frozen=True/slots=True，防止随手改 user_id 等字段；但 list、dict 和 budget 的内部状态仍可变。Runtime replace 注入事件 sink，SpecialistPool replace 改角色和层级，同时保留 budget、身份及 trace 关联；子 Agent 会单独建立 tool_observations，避免父子循环指纹混在一起。

## 权限与修改注意

RunContext.create 的 local_user_id 回退只适用于受信任调用，不是允许 HTTP 用户省略认证。不要把整个 context 序列化给模型、SSE 或日志。测试通过真实框架观察传入 context，并校验子图身份和 budget 对象共享。

## 相关源码说明

- [backend/app/auth.py](../auth.py.md)
- [backend/app/agent/budget.py](budget.py.md)
- [backend/app/agent/runtime.py](runtime.py.md)
- [backend/app/agents/subagents.py](../agents/subagents.py.md)
- [backend/tests/unit/test_runtime.py](../../tests/unit/test_runtime.py.md)

