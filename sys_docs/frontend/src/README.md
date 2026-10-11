# 浏览器应用源码目录

- 对应目录：`frontend/src/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../../frontend/src/) · [上级说明](../README.md)

## 组织目的

这里保存随 Vite 构建进入浏览器的源码与资产。main.tsx 挂载根组件并导入 styles.css；App.tsx 拥有连接、身份切换、导航与工作台布局；components 拆分业务交互，lib 集中 HTTP/SSE、资源 Hook 和类型。favicon.svg 作为构建资产被 HTML 引用。

界面状态尽量放在最小必要组件内：App 不直接编辑体重表单，Chat 不缓存所有文档，api.ts 不触碰 React。通过 props 和回调传递 token、可信 Session、threadId 及草稿，避免引入不必要的全局健康数据缓存。

本目录没有模型密钥、SQL 或 Agent 编排；任何显示都要依据服务端实际响应。开发 StrictMode 与异步取消逻辑共同帮助避免旧请求污染当前界面。

## 对应文件和子目录

- [components/](components/README.md)：目录说明。
- [lib/](lib/README.md)：目录说明。
- [App.tsx](App.tsx.md)：工作台入口、身份连接与页面编排。
- [main.tsx](main.tsx.md)：浏览器启动与 React 根挂载。
- [favicon.svg](favicon.svg.md)：浏览器标签页图标源资产。
- [styles.css](styles.css.md)：工作台视觉系统、页面布局与响应式样式。

