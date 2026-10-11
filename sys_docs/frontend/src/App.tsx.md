# 工作台入口、身份连接与页面编排

- 对应源码：`frontend/src/App.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../frontend/src/App.tsx) · [本目录说明](README.md)

## 这个文件解决什么问题

这是 React 应用的主装配层，包含默认导出的 `App`、内部的 `Workspace` 和 `ContextPanel`。它决定何时显示连接页、何时进入用户工作区，以及四个业务页面如何共享会话身份、导航和“正在执行”状态。真正的健康业务仍由后端接口执行。

## App：连接生命周期与凭据边界

- 首次挂载调用 `connect("")` 请求 `GET /api/session`。服务端处于本地模式时可以直接进入；需要 Bearer 认证时，401 被转换为访问凭据提示。
- `session` 是已确认的服务端身份和能力信息；`token` 是当前连接凭据；`input` 只是密码输入框草稿；`connecting/error` 表示连接状态。
- `connect` 先取消上一次连接请求、把 `session` 清空，再创建新的 AbortController。只在未取消时接受响应，避免较慢的旧连接覆盖新选择。
- 没有 session 时不挂载 Workspace。切换凭据通过 `disconnect` 清空 session/token/input，重置 hash 到 `/chat`，从而卸载旧工作区及其子组件。子组件清理自己的请求和健康数据内存。
- 访问凭据不是模型供应商 API Key。本文件没有读写 localStorage、sessionStorage，也不把凭据放进 URL；刷新会重新走连接流程。这里的隔离是浏览器状态隔离，最终权限仍由后端验证。

## Workspace：导航和交互状态

`readRoute()` 读取 hash，支持 `#/records`、`#/documents`、`#/memory` 以及 `#/chat/<UUID>`。会话 ID 必须匹配 UUID 外形；非法或未知页面退回 chat。采用 hash 避免刷新子页面时要求 FastAPI 提供任意路径的 SPA 回退。

| 状态 | 作用 |
|---|---|
| route | 当前页面以及可选 threadId |
| mobileNav / narrow | 控制 760px 及以下侧栏抽屉；隐藏侧栏同时设置 aria-hidden 和 inert |
| context | 打开资料与偏好辅助面板 |
| dark | 设置 HTML 根元素 data-theme；仅本次工作区有效，卸载时清除 |
| busy | Chat 告知任务是否执行中；限制新会话、主导航和历史会话跳转 |
| query | 对已获取会话标题做前端 includes 搜索，没有远端全文搜索 |
| draft | 文档提问等入口传来的草稿，key 变化用于让 Chat 重置新会话 |

`useResource("/api/threads")` 获取最近会话。标题没有值时显示“新对话”；`can_resume` 控制提示点。首次收到新对话的服务端 ID 后，`created` 更新 URL 并刷新历史。这里不会为“点击新对话”立即发 POST，实际新会话由第一次聊天请求创建。

## 业务组件之间的连接

- Chat 接收 token、session、threadId、初始草稿以及创建会话/刷新列表/忙碌变化/导航回调。
- Records 与 Memory 接收 token/session，自行读取业务数据。
- Documents 的 `onAsk` 只把带文件名的问题放入新对话草稿，用户仍需点击发送。
- ContextPanel 开启后独立读取 `GET /api/documents` 与 `GET /api/memory`。最多展示 8 个文档及已有偏好，提供管理入口；这些条目不是本轮回答的检索证据清单。
- 顶栏由服务端 `model_mode` 区分“演示模式”和“模型已连接”，不会由前端自行切换模型。

## 设计边界和维护注意

工作区没有全局状态库或第三方路由器；状态由组件树和 URL 协作维护。卸载整个工作区是切换身份时清除所有旧业务视图的核心。业务 API 失败通常留在相应页面展示，不会自动退出账户。修改 busy 或路由逻辑时，要同时检查流式对话自己的 threadId 保护，避免服务端刚分配会话 ID 就取消正在进行的请求。

相关说明：[Chat](components/Chat.tsx.md)、[资源 Hook](lib/hooks.ts.md)、[API](lib/api.ts.md)、[样式](styles.css.md)、[凭据切换浏览器测试](../tests/e2e/workspace.spec.ts.md)。

