- 对应源码：`backend/tests/integration/test_subagents.py`
- 核对日期：2026-10-04
- 阅读源码：[test_subagents.py](../../../../backend/tests/integration/test_subagents.py)
- 所属目录：[目录说明](README.md)

# 专业 Agent 权限、隔离、预算与并发测试

## 测试模型与控制方式

DelegatingModel 根据 RunContext.delegation_depth 决定“主图委派/子图查工具”，记录实际角色和绑定工具集合；收到 ToolMessage 后返回固定汇总。ConcurrencyModel 记录同时运行的 _agenerate 数量和峰值。两者都是测试模型，不是生产智能策略。

## 主要用例和断言

### 三角色端到端委派

test_lead_delegates_to_scoped_specialist_and_aggregates 参数化 record/nutrition/research。在另一个用户下播种指标/文档，在当前用户下播种自己的文档，通过真实 /api/chat 执行。检查报告角色、completed、真实 observation 成功；record 不看到他人指标，research 只引用当前用户文档；父会话可见历史仅用户与最终回答，子图消息不含父请求私有上下文标记；子 context 使用 local-user 并与父共享同一个 budget；子工具集合不含 delegate_health_task。

### 越权工具与递归禁止

test_specialists_cannot_write_or_delegate_recursively 故意让子模型调用 add_health_metric。报告 observation 失败，真实指标表保持为空。另用 depth=1 context 直接调用 SpecialistPool.run，得到 delegation_forbidden。

### 共享上限不能被子图重置

test_delegation_uses_shared_tool_budget 将工具预算设 1，父委派已消耗额度，子图再用工具应返回 503/tool_limit。
test_shared_model_and_delegation_budget_cannot_reset_in_child_graph 分别把共享模型上限设 1、委派上限设 1，第二个子任务触发 step_limit/delegation_limit，且模型调用数量不超额。

### 并发、超时与取消释放

test_subagent_capacity_timeout_and_cancel_release 同时跑三种任务，并发容量 2 时峰值为 2；更短时限得到 subagent_timeout；取消任务保持 CancelledError，随后新的任务仍可成功，证明容量没有永久占用。

## 覆盖边界

验证的是框架隔离、允许工具、身份和状态，而非模型分析健康资料的准确率。当前并发测试在同一进程/事件循环，不证明分布式队列公平性或多 worker 安全。父任务最小化传递由实际子消息断言验证，但 task 文本仍由 Lead 提供，系统提示词和代码边界必须持续配合。

## 修改注意

新增角色、工具 allowlist、报告 schema 或子配置传递时保持这些断言，尤其不要把完整父 config/messages 复制给子图。放宽写权限需要重新设计幂等/确认及测试，不是只更改集合名称。

## 相关源码说明

- [backend/app/agents/subagents.py](../../app/agents/subagents.py.md)
- [backend/app/agent/context.py](../../app/agent/context.py.md)
- [backend/app/agent/budget.py](../../app/agent/budget.py.md)
- [backend/tests/fakes.py](../fakes.py.md)
- [backend/tests/integration/test_reliability.py](test_reliability.py.md)

