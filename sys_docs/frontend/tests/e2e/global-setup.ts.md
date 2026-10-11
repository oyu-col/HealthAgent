# 测试拥有的 Vite 进程内生命周期

- 对应源码：`frontend/tests/e2e/global-setup.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/tests/e2e/global-setup.ts) · [本目录说明](README.md)

## 实现步骤

默认导出 async setup，调用 Vite createServer，明确 host=127.0.0.1、port=5173、strictPort=true，然后 await server.listen。启动失败先 await server.close，再原样抛错；启动成功返回 async teardown，测试结束 await server.close。

Playwright 在执行用例前调用 globalSetup，并在收尾执行返回的函数。整个服务由测试进程直接拥有，没有额外 PowerShell/cmd/npm 子进程链。

## 为什么这样设计

源码注释明确说明 Windows shell 的后代进程可能让 webServer teardown 挂起。通过 Vite 的编程接口启动和关闭，资源归属更清楚，也不需要按端口猜测应杀掉哪个用户进程。

strictPort 防止自动换端口导致测试访问错误页面；当前不自动复用外部已经启动的 5173 服务，端口冲突应由调用者解决。本文件不启动后端，E2E API 由 MockApi 拦截。

相关说明：[Playwright 配置](../../playwright.config.ts.md)、[开发代理配置](../../vite.config.ts.md)、[API 替身](mock-api.ts.md)。

