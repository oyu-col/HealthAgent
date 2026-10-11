# Chromium 工作台契约测试目录

- 对应目录：`frontend/tests/e2e/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../../../frontend/tests/e2e/) · [上级说明](../README.md)

## 文件协作

global-setup.ts 负责测试服务启动清理；mock-api.ts 定义每例独立的合成 API 与用户状态；workspace.spec.ts 通过真实 DOM 操作验证跨组件行为。Playwright 的项目、端口、失败 Trace 等配置在前端根目录。

这里的 e2e 指浏览器用户流程完整，不意味着下游模型、数据库也真实运行：所有 /api 请求被拦截，未知调用被记录并令 fixture 验证失败。截图为人工视觉检查证据，没有像素基线比较。

## 对应文件和子目录

- [workspace.spec.ts](workspace.spec.ts.md)：工作台的 Chromium 用户流程与布局测试。
- [mock-api.ts](mock-api.ts.md)：浏览器测试专用合成 API 和用户状态。
- [global-setup.ts](global-setup.ts.md)：测试拥有的 Vite 进程内生命周期。

