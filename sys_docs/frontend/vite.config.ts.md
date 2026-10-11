# Vite 开发代理与 Vitest 发现规则

- 对应源码：`frontend/vite.config.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/vite.config.ts) · [本目录说明](README.md)

## 应用构建和开发配置

使用 vitest/config 的 defineConfig，让同一配置同时识别 Vite 与 Vitest 字段；plugins 中的 React 插件处理 React/TSX 开发与构建。未改写 build 输出目录，因此生产输出使用 dist。

server.port=5173、strictPort=true：端口被占用时失败，不静默改到 5174，保证测试和使用说明地址确定。dev 脚本额外指定 --host 127.0.0.1；此文件没有监听全部网卡的配置。

## 同源代理

/api 和 /healthz 请求都代理到 http://127.0.0.1:8000。浏览器组件始终只请求本站路径，开发时由 Vite 转发；生产时则由 FastAPI 同时提供静态资源和 API，因此组件无需切换 URL 或接触模型凭据。

这不是独立跨域认证方案，也不会启动后端。开发机没有运行 8000 后端时，连接页会展示请求错误；E2E 的 page.route 拦截 API 后则可以不依赖真实后端。

## 单元测试配置

test.environment=node，include 仅 tests/unit/**/*.test.ts。传输测试使用 Node 提供的 fetch/Response/ReadableStream 等 API，不需要挂载浏览器 DOM。tests/e2e 的 Playwright 用例由另一个执行器负责，不会被此处扫描运行。

相关说明：[包脚本](package.json.md)、[API 同源限制](src/lib/api.ts.md)、[浏览器服务生命周期](tests/e2e/global-setup.ts.md)。

