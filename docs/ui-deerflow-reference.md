# HealthAgent UI：DeerFlow 参考与独立实现边界

核对日期：2026-10-03。本文依据本地 `D:/AgentFiles/deer-flow` 的真实源码，未运行或修改 DeerFlow，也未将其作为 HealthAgent 依赖。行号用于定位本次阅读位置，后续参考仓库更新可能改变行号。

## 本轮范围

规范第 28 节中，Phase 1–6 分别要求基础 Agent、健康工具与数据库、Thread / Checkpoint、Streaming、RAG、Memory。UI 工作最初用于补充 Phase 1–6 的操作入口，随后用户将目标扩展到 Phase 10；当前完整前端按 Phase 9 验收，覆盖 Chat、Thread、Streaming、Documents、Health Records，并增加偏好管理和 Trace 查看。专业 Agent 与可靠性仍按 Phase 7/8 单独验证。

这层 UI 应连接真实 API，支持会话历史、流式消息与恢复、文档上传及索引状态、偏好查看 / 更正 / 删除。健康记录入口需连接受服务端身份约束的 Service / Repository；不能用固定示例数字装成用户真实记录。默认 fake 模型是演示回显，应明确标识，其不会理解自然语言工具操作。不能把健康数据库和 Memory 混为一张“用户记忆”列表。

## 实际参考位置

以下路径均相对 `D:/AgentFiles/deer-flow/frontend/src/`。

| 位置 | 已阅读的设计 | HealthAgent 的独立借鉴 |
| --- | --- | --- |
| `app/workspace/workspace-content.tsx:23` | SidebarProvider 统一工作台外壳，主内容、离线提示和通知各自承担职责 | 左侧导航 / 会话，中央业务区域；连接状态有独立提示 |
| `components/workspace/workspace-sidebar.tsx:21` | Header / Content / Footer，左栏折叠，RecentChatList 独立 | 品牌与新会话在上，功能入口与历史在中，连接设置在下 |
| `components/workspace/recent-chat-list.tsx:227`、`:396` | 单行会话标题截断与完整 title，当前列表单独管理 | 会话列表显示可读标题 / 时间 / 当前选中状态，不以长 UUID 作唯一标签 |
| `components/workspace/welcome.tsx:21` | 无消息时居中欢迎，简短标题和说明 | 健康主题欢迎区与可编辑建议，不预填真实健康结论 |
| `components/workspace/chats/chat-box.tsx:85`、`:415`、`:465` | 桌面聊天 / 右侧详情面板；移动端 Sheet；面板互斥 | 桌面可打开文档 / 偏好详情，窄屏改抽屉或独立视图；无需复制可拖拽多面板系统 |
| `components/workspace/messages/message-list.tsx:1119` | 限宽消息区域，历史 / 正在生成内容独立；稳定消息身份 | 消息宽度适合阅读，保留完整历史，不因流刷新重复插入用户消息 |
| `components/workspace/messages/message-list-item.tsx:506` | 用户输入按纯文本显示，避免 Markdown 改写粘贴内容 | 用户输入与文档原文使用安全文本；模型输出若用 Markdown 必须限制协议与原始 HTML |
| `components/workspace/input-box.tsx:1199`、`:1324`、`:2022`、`:2420` | 提交验证，运行时阻止重复提交，停止入口，IME 组合输入保护，圆角独立输入区 | Enter 发送 / Shift+Enter 换行，中文输入法确认不误发送；发送中改停止；失败保留草稿与恢复入口 |
| `core/threads/hooks.ts:1962`、`:2118`、`:2141` | 流由统一 hook 管理；结束 / 错误后重新读取权威状态；处理旧会话响应 | UI 渲染与 API / SSE 解析分离；切换会话时取消过期读取，迟到响应不能覆盖新会话 |
| `components/workspace/gateway-offline-banner.tsx:25` | 离线与认证状态分开，避免重叠请求，恢复后消除提示 | 不能把 API 请求失败展示为空列表；提供具体错误与重新连接 |
| `components/workspace/artifacts/artifact-viewer.tsx:19` | 文件身份清晰，加载 / 错误 / 内容分支，长预览有界 | 文档列表显示文件名、解析及索引状态；不复制代码编辑、任意文件执行或沙箱浏览器 |
| `components/workspace/knowledge-scope-selector.tsx:54`、`:239` | 文档选择有搜索、分页、加载与权限状态；选择不等于授权 | 当前只展示后端允许的个人文档，不添加客户端切换 user_id 或随意发布公共知识的控件 |
| `core/knowledge/sources.ts:23`、`components/workspace/citations/knowledge-source.tsx:28`、`:78`、`:91` | 引用只能从已验证检索来源解析；缺失来源不能伪装可打开；原文按纯文本展示 | 若提供引用详情，必须有后端实际 citation_id / 文件 / 页码 / 原文；不能从模型文本编造来源卡片 |
| `components/workspace/settings/memory-settings-page.tsx:242`、`:429`、`:479`、`:501` | Memory 有读取、编辑、删除以及显式 pending / error 分支 | 按 HealthAgent allowlist 显示饮食、运动、风格、语言偏好，保存成功后刷新，失败不假装成功 |

## 视觉和布局

`styles/globals.css:248` 起采用暖白背景、接近黑色的主文本、低饱和辅助色和浅边框；基础圆角为 `0.625rem`。`:457` 起以 CSS 变量集中管理内容宽度，消息 `md` 宽度为 `204 × spacing`。这说明应借鉴的是统一 token 和克制的阅读布局，而非照搬所有组件。

HealthAgent 可以独立定义暖白底色、略深左栏、深色文本、健康主题绿色强调；约 250px 左栏、约 800px 消息区，圆角输入框和轻边框卡片。状态应同时有文字，不能只靠颜色。窄屏收起左栏，保持输入框可达、表单无横向溢出。按钮具备可见焦点与文字 / aria-label；加载和错误应被辅助技术读出；动画遵循 reduced-motion。

## 流状态和错误恢复

HealthAgent 使用自己的 FastAPI SSE 契约，不接入 DeerFlow 的 LangGraph 平台兼容 SDK：

1. 创建 / 选择 thread；发送前生成并保留 request_id。同一运行期间阻止重复提交。
2. 读取 `run.started`，随后将 `message.delta` 逐步显示；`tool.started` / `tool.finished` 只展示真实工具名和状态，不展示未经筛选的健康原文或工具内部载荷。
3. 只有 `run.completed` 才成功，其 `answer` 替换临时流文本。HTTP 200 或读取到 EOF 均不代表完成。
4. `run.failed`、网络错误、停止及断线分别有可理解状态。保留原 request_id，并重新读取 thread 的 can_resume / status 与持久消息，再显示恢复入口。pending 不能单独决定恢复资格；后台确已完成时使用权威持久消息。恢复不能创建新 request_id 重跑可能已提交的写操作。
5. 当前后端不支持 Last-Event-ID 重放，不复制 DeerFlow 自动 rejoin 的承诺。停止后需要等待服务端运行结束或刷新 pending 状态，避免立即发送导致 thread_busy。
6. SSE 解码必须使用增量 UTF-8，并处理任意帧边界；检查协议版本 / 事件序号 / 终态。跨会话读取用 AbortController 或 generation guard，避免旧响应污染新视图。

文档上传先检查 2 MiB 和支持的扩展名，服务端校验为最终依据。索引失败展示保留的失败状态，可选择原文件再次上传。Memory 修改以服务端返回为准；仅更改对应 preference key，失败保留编辑值。Token 只发到应用明确配置的后端，不写入浏览器持久存储、URL、日志或 UI 截图。

## 不照搬的部分

DeerFlow 的模型 / 模式选择、Skills / MCP / Plugin、Multi-Agent 任务树、沙箱浏览器、任意 Artifact 编辑、侧车引用、历史压缩编织、分支 / 编辑重跑、项目权限与账号系统均有独立后端契约。本阶段不增加只有外观没有实现的入口，不复制其数千行 hooks / InputBox，不宣称支持事件重放或后台继续执行。

可保留的工程模式是：展示组件与数据逻辑分离、可信状态来自服务端、请求按用户和会话隔离、加载 / 失败 / 空状态分开、写入后刷新实际数据，以及 UI 的操作权限不能替代服务端授权。

## 验证边界

本文是源码参考记录，不是 UI 已实现或已测试的声明。具体实现、构建、交互验收及剩余限制由本轮交付记录列出；DeerFlow 未被安装、启动或修改。
