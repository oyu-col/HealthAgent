# memory.py：显式长期偏好服务

- 对应源码：`backend/app/services/memory.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/services/memory.py) · [目录说明](README.md)

## 为什么单独有 MemoryService

这个服务只管理允许集合中的稳定偏好，不把健康事实、任意对话摘要或外部文档写成长期记忆。它为 Agent 中间件和偏好管理 API 提供统一入口，下层为 [MemoryRepository](../persistence/memory_repository.py.md)，提取规则位于 [extraction.py](../memory/extraction.py.md)。

## 方法契约

- extract(user_id,text,request_id,thread_id)：用保守语法提取当前用户文本；没有变化直接返回 []，有变化调用 apply，并保留来源请求/会话。返回真正应用的 key/value 变化列表。
- update(user_id,key,value)：检查 key 和 value 均在 ALLOWED_VALUES；value=None 表示删除。非法值抛 invalid_preference / 422。每次管理调用创建新 UUID 回执，thread_id=None。
- list(user_id)：列出该用户现存偏好及更新时间、来源标识。
- relevant(user_id,query)：总是允许 language、response_style；含饮食/食物/吃/营养/餐/diet/food/meal 时加 diet_preference；含运动/锻炼/健身/跑/游泳/exercise/workout 时加 exercise_preference。只返回所选 key 且值仍合法的条目。

## 隔离、回放和限制

user_id 必须来自可信调用方。自动提取用原 request_id 去重；管理接口每次生成新标识，因此不是“同 UUID 的客户端幂等 API”，而是对当前值进行重复赋值/删除。数据库回执能阻止旧对话恢复时重新写回已被更正或忘记的偏好。

relevant 使用关键词匹配，不是语义检索；可能漏掉同义表达，也不推断饮食禁忌。它假定存量 key 来自 allowlist，数据库被绕过 Service 写入非法 key 时不能视为有完整自愈能力。MEMORY_ENABLED 开关由中间件控制，Service 自身没有总开关，关闭自动 Memory 后管理 API 仍能使用。

## 调用与验证

[PreferenceMemoryMiddleware](../memory/middleware.py.md) 先 extract 再在模型调用时 relevant；API GET/PUT/DELETE 直接管理偏好。[测试](../../tests/integration/test_memory.py.md) 覆盖跨会话/重启、纠正删除、隔离、禁用自动写入和回放不复活。新增偏好需同步 allowlist、提取表达式、相关性规则、前端标签和测试，不能仅在数据库加任意自由文本。
