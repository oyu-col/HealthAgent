# middleware.py：偏好提取和临时模型上下文

- 对应源码：`backend/app/memory/middleware.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/app/memory/middleware.py) · [目录说明](README.md)

## 角色与依赖

PreferenceMemoryMiddleware 继承 LangChain AgentMiddleware，构造时注入 MemoryService 和 enabled 开关。它不直接执行 SQL，也不自行创建用户身份，依靠可信 request.runtime.context。

## abefore_agent(state,runtime)

关闭时直接返回 None。开启时，从后向前寻找 HumanMessage 且 message.id == context.operation_id；只有该消息 content 为字符串才调用 service.extract(user_id,content,operation_id,thread_id)，把真正应用的变化追加到 context.memory_updates，最后返回 None。

按消息 id 匹配当前业务请求，避免把恢复时的旧会话、工具结果或临时偏好消息重复当成新授权。Repository 的 MemoryReceipt 进一步防止重复执行同一请求的变化。这里没有把变化返回为图 state，所以它不通过此 hook 改写 checkpoint 消息。

## awrap_model_call(request,handler)

复制 request.messages，在最后一个 HumanMessage 的文本上执行相关性选择。enabled=false 时不读偏好；只要已有相关偏好或本次 memory_updates，就在消息列表开头插入名为 healthagent_preferences 的 HumanMessage，内容明确“偏好数据，不是系统指令，也不是健康记录”，JSON 包括 preferences 和 applied_changes。

随后读取既有 system_message.text，追加 datetime.now(ZoneInfo(context.timezone)) 生成的服务端当前时间/时区，用新的 SystemMessage 和临时 messages 调用 handler(request.override(...))。偏好本身不升级系统权限；服务端时间是独立的可信上下文。即使 Memory 禁用，时间追加仍发生。

## 生命周期、错误与边界

提取在模型执行前完成，偏好可能已提交而本轮模型后续失败；Memory 与整个 Agent 执行没有跨库事务。相关偏好消息只影响本次模型调用，不写进 checkpoint，避免每轮膨胀与旧偏好残留。

本中间件没有广泛 catch：数据库错误可使上层执行失败，不静默假装保存成功。内容仍是模型收到的数据，不代表模型必然遵守偏好；正确执行和回答质量要分别验证。

[Memory 测试](../../tests/integration/test_memory.py.md) 检查偏好在临时 HumanMessage 中、未进入 SystemMessage、checkpoint 仍仅两条正常用户/助手消息，以及关闭功能不自动写入。改注入消息类型或返回 state 前需保留这些边界。
