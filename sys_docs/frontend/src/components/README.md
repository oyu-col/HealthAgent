# 健康工作台业务组件与基础组件

- 对应目录：`frontend/src/components/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../../../frontend/src/components/) · [上级说明](../README.md)

## 组件分工

Chat 负责完整对话生命周期；Records 负责结构化记录的查询和表单；Documents 管理私人文档与笔记；Memory 管理 allowlist 偏好；TraceDialog 展示单次运行元数据；ui.tsx 提供共享反馈、标题和原生 dialog。

这些组件经 props 获取 token/session，不自己读取持久化凭据。只读页面使用 useResource，写入和聊天各自拥有 AbortController。父级 App 在身份切换时卸载所有业务组件，触发清理；后端继续负责真正的用户隔离和授权。

API 的 HTTP 成功、ToolResult.success、文档 index_status、SSE run.completed 具有不同语义，组件必须各自检查适用的完成条件。不要把所有 200 响应统一显示成业务成功。

## 对应文件和子目录

- [Chat.tsx](Chat.tsx.md)：对话、流式事件与中断恢复。
- [Records.tsx](Records.tsx.md)：身体指标、饮食和运动记录界面。
- [Documents.tsx](Documents.tsx.md)：私人文档上传、笔记创建与提问草稿。
- [Memory.tsx](Memory.tsx.md)：长期偏好的查看、修改与确认忘记。
- [TraceDialog.tsx](TraceDialog.tsx.md)：执行 Trace 指标和事件时间线。
- [ui.tsx](ui.tsx.md)：通用展示组件与原生弹窗。

