# Playwright 浏览器契约测试配置

- 对应源码：`frontend/playwright.config.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/playwright.config.ts) · [本目录说明](README.md)

## 发现和执行策略

testDir 指向 ./tests/e2e，fullyParallel=true，测试各自拥有独立 MockApi fixture。CI 环境 forbidOnly 防止遗留 test.only，失败重试 1 次，workers 固定为 2；本地不自动重试，workers 使用 Playwright 默认策略。reporter 为 list。

projects 仅有 chromium，使用 Desktop Chrome 设备设置。移动测试通过用例中的 setViewportSize 模拟窄屏布局，并非额外的移动系统浏览器项目，因此当前配置不能证明 Firefox、WebKit 或真实触摸设备兼容性。

## 浏览器与产物

baseURL 固定 http://127.0.0.1:5173；trace=retain-on-failure，screenshot=only-on-failure；serviceWorkers=block，确保接口路由拦截不会被 Service Worker 绕开。部分用例另行主动截图到 test-results/ui-review。

globalSetup 指向 tests/e2e/global-setup.ts，使用同进程 Vite 生命周期，配置本身没有 webServer 字段，也不会自动借用已经运行的任意开发服务。5173 被占用会失败，而非测试错项目。

## 验证边界

这些测试在真实 Chromium 中渲染真实 React 页面，但业务 API 被 MockApi 截获，主要验证 UI 与后端契约、状态转换和布局。它们不验证真实数据库、RAG embedding 或供应商模型；真实后端页面联调由 scripts/smoke.mjs 负责。

相关说明：[服务 setup](tests/e2e/global-setup.ts.md)、[浏览器用例](tests/e2e/workspace.spec.ts.md)、[合成 API](tests/e2e/mock-api.ts.md)。

