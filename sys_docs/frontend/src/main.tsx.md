# 浏览器启动与 React 根挂载

- 对应源码：`frontend/src/main.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../frontend/src/main.tsx) · [本目录说明](README.md)

## 执行入口

index.html 的模块脚本加载本文件。它导入 React StrictMode、react-dom/client 的 createRoot、App 和 styles.css，然后找到 DOM 中 id=root 的容器创建 React 根并渲染 App。

非空断言 `document.getElementById("root")!` 体现与 index.html 的契约：HTML 必须先提供 root 容器。这里没有异步获取配置、模型密钥或服务端用户数据；这些事情由 App 通过同源接口处理。

## StrictMode 的目的和影响

整个组件树放在 StrictMode 中，帮助开发环境暴露副作用与清理问题。开发时 effect 可能经历额外挂载/清理，因此网络请求要能取消，测试也不能简单断言每个只读 effect 绝对只执行一次。Trace 的浏览器测试允许 1–2 次 GET 正是考虑这个行为。

样式只在入口统一导入，避免每个组件手工重复引入。Vite 将该入口及其依赖构建为生产静态资源。

相关说明：[HTML 容器](../index.html.md)、[App](App.tsx.md)、[样式](styles.css.md)、[构建配置](../vite.config.ts.md)。

