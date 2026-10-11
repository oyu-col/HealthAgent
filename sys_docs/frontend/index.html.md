# HTML 外壳与构建资产入口

- 对应源码：`frontend/index.html`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/index.html) · [本目录说明](README.md)

## 页面基本信息

这是 Vite 应用的 HTML 入口，不是服务器端模板。lang=zh-CN、UTF-8 编码与 viewport 支持中文和移动布局；theme-color=#f8f9f7 提供浏览器 UI 主题提示；description 描述健康记录产品；title 为“HealthAgent · 个人健康工作台”。

## 两个连接点

body 中的 div#root 供 main.tsx 挂载 React；type=module 脚本 src=/src/main.tsx 建立源码依赖图。favicon 指向 /src/favicon.svg，构建时交给 Vite 改写成 /assets 的哈希文件，而非要求 FastAPI 单独提供 /favicon.svg。

本文件没有内联 token、健康资料、供应商配置或外部 CDN 脚本。生产运行时，FastAPI 提供构建后的 dist/index.html，不能把当前源码入口 HTML 直接当作未经构建的生产可执行页面。

相关说明：[React 入口](src/main.tsx.md)、[favicon](src/favicon.svg.md)、[Vite](vite.config.ts.md)。

