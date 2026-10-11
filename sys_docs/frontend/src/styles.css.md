# 工作台视觉系统、页面布局与响应式样式

- 对应源码：`frontend/src/styles.css`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../frontend/src/styles.css) · [本目录说明](README.md)

## 文件承担的角色

这是入口 main.tsx 一次性导入的全局 CSS，覆盖连接页、工作台、对话、记录、文档、偏好、弹窗和执行 Trace。项目没有 Tailwind、CSS Modules 或第三方整套 UI 样式框架；className 与组件代码直接对应。DeerFlow 的侧栏、中心消息区、composer 和辅助面板是设计参考，本文件是本项目独立样式。

## 主题和通用基础

:root 定义字体、抗锯齿、14px 基准以及 --bg、--panel、--sidebar、--text、--muted、--line、--accent、--accent-soft、--hover、--danger、--shadow。浅色主背景 #fafbf9、侧栏 #f1f3ef、健康主题绿 #2c6b51；:root[data-theme="dark"] 换成深色变量并设置 color-scheme:dark。主题切换由 App 状态控制，CSS 本身不持久化偏好。

通用层统一 box-sizing、表单字体、按钮禁用态、焦点轮廓、输入焦点、链接和选中颜色。visually-hidden 隐藏文件输入框的视觉显示但保留可访问语义；mobile-only 根据断点切换。spin、blink 表达加载和处理状态。

## 布局层次

| 选择器 | 布局目的 |
|---|---|
| workspace | 100dvh 横向 flex，限制外层溢出 |
| sidebar | 默认 250px 固定宽度、独立历史区和底部账户区 |
| workspace-main / main-surface | 主区可伸缩，min-width/min-height 避免 flex 撑破；内容区纵向滚动 |
| topbar | 69px 桌面顶栏、导航标题和主题/资料操作 |
| chat-workspace | 最大 840px（包含左右 padding）的居中对话容器 |
| composer | 18px 圆角、浅边框、阴影，内部文本区和按钮工具条 |
| context-panel | 宽屏侧边辅助资料；小屏改为覆盖层 |
| dialog | 原生 dialog 与 backdrop；wide 版供笔记与 Trace 使用 |

欢迎页标题使用中文衬线字体回退，正文仍用系统无衬线；没有下载外部字体的声明。用户消息靠右并保留换行，助手正文支持 Markdown 段落、代码、表格、引用和列表。代码和表格允许局部横向滚动，长文可换行，减少整个页面横向溢出。

## 业务页样式

record-overview 是静态介绍卡片；record-list/record-row 组织实测数值与日期。upload-zone 含 dragging 状态，document-row 体现文件类型及索引结果。memory-intro、preference-grid/card 显示偏好及更新信息。统一的 error-notice/success-notice/loading/empty-state 区分操作结果。trace-metrics、trace-details、trace-timeline 显示统计与事件，失败圆点使用 --danger；未知量由组件输出占位，不靠颜色猜测。

## 响应式与无障碍

- 高度至少 950px 时欢迎区增加顶部留白。
- 宽度至多 1200px：侧栏 224px，辅助面板改绝对定位覆盖右侧。
- 宽度至多 760px：侧栏变为 270px 抽屉，配 nav-scrim 遮罩；topbar 改 60px，隐藏冗余面包屑，欢迎卡片改纵向，表单与列表收紧。
- 同一手机断点下 Trace 指标由四列变为两列；辅助面板最大占 90vw。
- prefers-reduced-motion:reduce 时关闭动画、平滑滚动和过渡。

CSS 负责视觉隐藏，App 同时给关闭的手机侧栏 inert/aria-hidden，两者需要保持断点一致。布局变更宜对照已有 1440×1000 和 390×844 浏览器场景；截图存在不等于已做像素级回归比对。

相关说明：[App 布局状态](App.tsx.md)、[公共组件](components/ui.tsx.md)、[浏览器布局测试](../tests/e2e/workspace.spec.ts.md)。

