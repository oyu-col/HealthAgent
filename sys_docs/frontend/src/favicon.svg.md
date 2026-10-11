# 浏览器标签页图标源资产

- 对应源码：`frontend/src/favicon.svg`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../frontend/src/favicon.svg) · [本目录说明](README.md)

## 内容与设计

一个 40×40 的内联 SVG 源文件，viewBox 同尺寸；绿色填充的圆角矩形背景上叠加白色心电折线，圆角线帽和连接让小尺寸显示更清楚。它是静态品牌图标，不包含脚本、远程图片、健康数据或交互逻辑。

## 为什么位于 src

index.html 使用 /src/favicon.svg 引用。构建时 Vite 将它作为受管资产处理，输出到 dist/assets 的带内容哈希资源并重写 HTML 引用。当前 public 目录为空，不应寻找 public/favicon.svg。

这与 FastAPI 生产静态路由配合：构建后的资源由 /assets 提供，避免把 favicon 放在 dist 根后要求另开一个根路径文件路由。页面内品牌方块则来自 ui.tsx 的 Brand + lucide 图标，不是直接复用这个 SVG。

相关说明：[HTML 引用](../index.html.md)、[空 public 目录](../public/README.md)、[Brand 组件](components/ui.tsx.md)。

