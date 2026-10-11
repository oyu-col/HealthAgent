- 对应源码：`backend/app/api/threads.py`
- 核对日期：2026-10-04
- 阅读源码：[threads.py](../../../../backend/app/api/threads.py)
- 所属目录：[目录说明](README.md)

# 会话管理与恢复 HTTP 接口

## 定位与接口

路由前缀为 /api/threads，所有接口都要求 UserDependency，并将实际逻辑委托给 ThreadService。
| 接口 | 调用与结果 |
| --- | --- |
| POST /api/threads | threads.create(user_id)，创建空会话并返回 ThreadMetadata。 |
| GET /api/threads | threads.list(user_id)，以 threads 数组返回当前用户会话元数据。 |
| GET /api/threads/{thread_id} | 将经过 UUID 校验的 ID 传给 threads.state，返回元数据与可见用户/助手消息。 |
| POST /api/threads/{thread_id}/resume | 接收必填 request_id，通过 chat.execute_chat(resume=True) 恢复原请求并返回 ChatResponse。 |

## 设计目的与调用关系

将“管理会话”与“执行一轮普通对话”分开，但恢复复用同一执行收尾逻辑，避免出现两套成功回执或异常处理。前端侧栏、历史加载和中断恢复均使用这一组接口。

## 权限和状态边界

路由本身不读取 checkpoint，也不直接决定 can_resume。真实归属检查、只返回可见消息、同线程并发冲突、未完成请求约束全部由 ThreadService 完成。URL 中的 thread_id 只是待查标识，不是授权；不存在和不可见会话都应由下游安全处理。
恢复请求没有 message 字段，不能借恢复偷偷追加新用户输入。request_id 必须对应原始业务请求；不是新建一轮执行的任意标签。响应中会有新的执行 run/trace 标识，但仍关联原业务请求。

## 验证与修改注意

test_threads 验证重启后的历史、同请求重复返回、改内容冲突、写后失败恢复不重复写、跨用户访问 404 以及同线程并发一成一拒。增加新路由时继续复用用户依赖和服务层，避免让客户端传 configurable/checkpoint 原始配置。

## 相关源码说明

- [backend/app/api/chat.py](chat.py.md)
- [backend/app/api/schemas.py](schemas.py.md)
- [backend/app/services/threads.py](../services/threads.py.md)
- [backend/tests/integration/test_threads.py](../../tests/integration/test_threads.py.md)

