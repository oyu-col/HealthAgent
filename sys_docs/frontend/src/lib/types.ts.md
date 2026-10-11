# 页面状态与服务端协议的共享 TypeScript 类型

- 对应源码：`frontend/src/lib/types.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/lib/types.ts) · [本目录说明](README.md)

## 为什么集中定义类型

该文件只包含 type 声明，没有运行时代码、网络请求或数据库模型。它把多个组件共同使用的 API 形状集中在一起，使改字段时 TypeScript 可以提示受影响的调用者。真正的输入校验与授权仍位于后端；此处不会自动把 JSON 转成可信结构。

| 类型 | 当前字段和使用场景 |
|---|---|
| View / RecordKind | 四个页面 chat/records/documents/memory；三类记录 metric/diet/exercise |
| Session | 服务端 user_id、fake/provider 模式、timezone、memory_enabled，供工作区身份和提示使用 |
| Thread | thread_id、created_at、active_request_id，及可选 title/status/can_resume |
| ThreadState | 在 Thread 上增加 messages 与 pending，读取一个会话时使用 |
| Message | 仅 user/assistant 两种可见角色与 content；不是底层 LangGraph 全消息结构 |
| ToolResult<T> | success、可空 data、error_code、error_message、retryable |
| HealthRecord | 一份兼容三类记录的 UI 结构，id 必需，其余类型特有字段大多 optional |
| HealthDocument | 文件名、类型、创建时间、解析/索引状态与可选错误/可见范围 |
| Preference / MemoryData | 偏好键值、更新时间、来源请求/会话，以及服务端允许值集合 |
| ChatInput | message、可选 thread_id、必需 request_id |
| ChatResult | 完整答案、thread/request/run/trace 标识、模型模式、completed 终止原因、偏好变更 |
| StreamEvent | 六种事件名和共享 envelope，事件细分字段采用 optional 与索引签名 |

## 重要设计含义

Thread.active_request_id 和 ChatInput.request_id 是恢复及去重的请求身份，不是用户身份；user_id 只由 Session 展示，不被此处混入模型工具参数。can_resume 是服务端针对真实 checkpoint 给出的提示，pending 不代表一定能够恢复。

HealthRecord 采取宽松组合对象方便同一列表渲染，没有用三种 discriminated union 严格排他；组件要结合 kind 与 metric_type 判断字段。Trace 类型目前定义在 TraceDialog 内，尚未纳入本文件。

StreamEvent 的 TypeScript 类型不足以表达“tool.finished 必须有 success”或“序号连续”，这些由 api.ts 的运行时校验补足。不能因为 requestJson<T> 编译通过，就认为后端返回值已验证。

相关说明：[SSE 校验](api.ts.md)、[记录渲染](../components/Records.tsx.md)、[Trace 局部类型](../components/TraceDialog.tsx.md)。

