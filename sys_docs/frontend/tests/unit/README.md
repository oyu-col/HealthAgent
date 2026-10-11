# Node 环境的传输单元测试目录

- 对应目录：`frontend/tests/unit/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../../../frontend/tests/unit/) · [上级说明](../README.md)

## 目录目的

目前只有 api.test.ts，按 vite.config.ts 的 tests/unit/**/*.test.ts 规则被 Vitest 发现，pnpm test 单次运行。通过可控 Response/ReadableStream 和 fetch 替身构造错误、取消、EOF、身份污染等难以用真实服务器稳定触发的边界。

这些测试不需要真实用户资料、服务端密钥或浏览器。添加新传输行为时应优先补能观察外部契约的案例，而非只照抄实现内部步骤。

## 对应文件和子目录

- [api.test.ts](api.test.ts.md)：HTTP 与 SSE 传输契约的单元测试。

