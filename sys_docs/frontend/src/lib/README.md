# 前端共享协议、传输和资源工具

- 对应目录：`frontend/src/lib/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../../../frontend/src/lib/) · [上级说明](../README.md)

## 三个文件的层次

types.ts 描述编译期形状；api.ts 处理同源 fetch、标准错误和严格 SSE；hooks.ts 把普通只读 JSON 请求包成 React 生命周期，并提供错误/时间格式化。业务组件依赖这层，本层不反向导入业务组件。

共享传输保证当前凭据不会被旧 headers 覆盖，流只有完整 final 事件才成功，异常携带可恢复身份。共享 Hook 保证路径切换和卸载时不接纳旧响应，但它不是数据库，也不是跨用户长期缓存。

## 对应文件和子目录

- [api.ts](api.ts.md)：同源 HTTP 客户端与严格 SSE 解码器。
- [hooks.ts](hooks.ts.md)：资源读取 Hook 与时间、错误格式化。
- [types.ts](types.ts.md)：页面状态与服务端协议的共享 TypeScript 类型。

