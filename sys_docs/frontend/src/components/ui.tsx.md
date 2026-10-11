# 通用展示组件与原生弹窗

- 对应源码：`frontend/src/components/ui.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/ui.tsx) · [本目录说明](README.md)

## 本文件的设计目的

集中实现多个业务页重复使用的反馈和排版，保持样式、可访问属性及弹窗行为一致。这些组件不读取 API，也不保存用户身份；数据和具体操作全部由 props 提供。

| 导出 | props 与作用 |
|---|---|
| Brand | small 可选，生成 Activity 图标的品牌方块；aria-hidden=true，作为装饰 |
| EmptyState | icon、title、children、可选 action；统一无数据状态与引导操作 |
| ErrorNotice | message、可选 retry；role=alert；仅收到 retry 才显示重试按钮 |
| Loading | 可选 label，默认“正在加载…”；role=status 和旋转图标 |
| Dialog | title、children、onClose、可选 wide；原生 HTML dialog 模态窗口 |
| SectionHeading | eyebrow、title、description、可选 action；页面标题与操作区域 |

## Dialog 的生命周期

ref 指向 HTMLDialogElement；首次 effect 调用 showModal，卸载时移除 cancel 监听并 close。closeRef 每次 render 更新，供一次注册的监听获取最新 onClose，避免 effect 因回调变化反复开关弹窗。

用户按 Escape 触发原生 cancel 事件，本组件 preventDefault 后交由业务 onClose 处理；点背景仅当 event.target===event.currentTarget 时触发；右上角按钮名称为“关闭弹窗”。这允许表单在 busy 时拒绝关闭，而不是让浏览器自行关掉一个仍在提交的窗口。

标题通过 aria-labelledby 指向 dialog-heading；当前页面设计每次仅有一个主要业务弹窗。如未来允许多个同时挂载，需要为标题 ID 做唯一化，不能假设固定 ID 足够。焦点与模态交互利用原生 dialog，而非自定义 div 模拟。

## 样式和业务边界

组件只选择 className，视觉定义在 styles.css。错误组件不会自动重发请求；调用者必须明确把合适的 reload 或重试动作传入。Dialog 不知道“取消是否丢失草稿”或“删除是否需要二次确认”，这些规则在 Records、Documents、Memory 实现。

相关说明：[全局样式](../styles.css.md)、[记录表单](Records.tsx.md)、[偏好删除确认](Memory.tsx.md)、[Trace 弹窗](TraceDialog.tsx.md)。

