# 对话、流式事件与中断恢复

- 对应源码：`frontend/src/components/Chat.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/Chat.tsx) · [本目录说明](README.md)

## 职责与输入输出

`Chat` 是整个前端最主要的状态协调组件。它通过 `streamChat` 显示增量、通过普通 JSON 请求读取历史或恢复 checkpoint；本身不运行模型或工具。输入 props 为 token、session、可选 threadId、initialDraft，以及 onThreadCreated、onThreadsChanged、onBusyChange、onNavigate 回调。

## 状态分组

| 组别 | 变量与含义 |
|---|---|
| 内容 | messages 为已接纳消息；draft 为输入草稿；streaming 为当前临时增量 |
| 运行 | busy 为正在提交/恢复；loading 为历史读取；tools 为本轮工具状态 |
| 异常 | error 为可读提示；incomplete 标记临时内容未完成；recoverable 提示先恢复旧请求；blocked 禁止在不可恢复的失败线程继续提交 |
| 观察 | traceId 标识最近一次执行；showTrace 控制执行记录弹窗 |
| 非渲染引用 | active 保存原始 ChatInput、实际 threadId、AbortController；resumeId 保存请求标识；historyController 取消历史请求；alive 防止卸载后接纳响应 |

## 读取历史与会话切换

threadId、凭据或 initialDraft 变化时，effect 先取消旧请求、清空消息、工具、错误和 Trace。如果 threadId 正好是 active 请求刚拿到的 ID，则提前返回，避免一次新对话因 URL 更新而被自己中止。

历史接口是 `GET /api/threads/{id}`。返回消息替换当前 messages。根据 `can_resume` 或 `status === "running"` 展示恢复入口，并保存 active_request_id；不能只使用 pending 判断。若状态为 failed 且没有可恢复节点，则进入 blocked，提示新建会话。卸载时中止聊天与历史请求，并向父组件释放 busy 状态。

## 正常发送的完整过程

1. `send` 检查 busy/loading/blocked/recoverable 及非空草稿；普通发送创建新的 UUID request_id，重试则复用 active 中原始请求。
2. 立即在页面追加用户消息并清空草稿，同时重置上一轮临时增量和工具列表。
3. 发送 `POST /api/chat/stream`。收到 run.started 后先把真实 threadId 写入 active，再通知父级更新 hash。
4. message.delta 只拼接 streaming；tool.started 新增工具条目，tool.finished 更新成功或失败标志。toolNames 将后端工具名映射为中文，包括专业委派。
5. `streamChat` 成功返回的 ChatResult 才交给 acceptResult：以 result.answer 追加最终助手消息，清空临时增量和未完成标记，保留 Trace ID，刷新会话列表。

此处特意不把临时增量直接转成持久答案，因为工具前后的多个模型调用可能产生不同片段，服务端 run.completed.answer 才是当前协议的最终结果。

## 停止、断线与恢复

停止按钮调用 active.controller.abort，不等同于服务端已经回滚。捕获 AbortError 后提示“内容尚未完成”；ApiError 中带回的 threadId/traceId 用于重新定位。随后 `refreshRecovery` 查询服务端状态：若线程已经 idle 且末尾为 assistant，接纳服务端消息；若仍可恢复或运行中，保留恢复入口；若终止且无可恢复节点，则阻止继续提交。

已知 threadId 时，`resume()` 调用 `POST /api/threads/{id}/resume`，请求体仅包含原 request_id。成功后重新读取完整历史以减少重复追加；若刷新历史失败，才使用已成功恢复返回的 answer 作为界面回退。若最初连接失败且从未取得 threadId，恢复会回到 `send(true)`，重发保存的原始 ChatInput，而非生成新的 request_id。resume_unavailable 会关闭恢复入口。

这套逻辑解决“前端断了但写操作可能已完成”的不确定性。可靠幂等和 checkpoint 的实际保证仍在后端，而不是依靠页面变量完成。

## 消息呈现与安全

内部 Markdown 使用 react-markdown + remark-gfm，开启 skipHtml；原始 HTML 不作为可执行界面渲染。链接新窗口打开并带 noopener/noreferrer。图片组件被替换为说明文字，不自动请求模型生成的远程图片。用户消息直接作为 React 文本显示。未完成内容带独立样式和标签；工具完成与模型最终完成分别展示，不能混为一谈。

输入最多 8000 字符；Enter 提交、Shift+Enter 换行，输入法组合状态不提交。附件按钮跳转文档页，不直接附加文件到聊天请求。首页三张入口卡片执行真实导航；两个建议按钮仅填充草稿。fake 模式明确说明不提供真实健康分析。Trace 按钮打开 [TraceDialog](TraceDialog.tsx.md)，历史页面目前不通过线程反查全部 Trace，因此仅有当前组件获知的 traceId 时显示。

相关说明：[传输及 SSE 校验](../lib/api.ts.md)、[共享类型](../lib/types.ts.md)、[上层导航](../App.tsx.md)、[跨组件恢复测试](../../tests/e2e/workspace.spec.ts.md)。

