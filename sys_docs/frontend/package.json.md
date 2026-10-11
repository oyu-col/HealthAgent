# 前端包元数据、依赖与开发命令

- 对应源码：`frontend/package.json`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/package.json) · [本目录说明](README.md)

## 元数据

包名 health-agent-ui、版本 0.1.0，private=true 防止误发布为公共 npm 包，type=module 使用 ES Module。packageManager 指定 pnpm@11.25.0，engines.node 要求 >=22.12.0。它描述源码依赖范围，具体安装结果由 pnpm-lock.yaml 固定。

## 命令实际做什么

| pnpm 命令 | 实际脚本与作用 |
|---|---|
| dev | vite --host 127.0.0.1，启动仅回环监听的开发页面 |
| build | tsc --noEmit && vite build，类型检查通过后生成 dist |
| typecheck | tsc --noEmit，只检查，不产出 JS |
| test | vitest run，单次运行 unit 测试 |
| test:e2e | playwright test，浏览器契约测试，服务由 global-setup 管理 |
| lint | eslint src tests，只对源码与测试运行静态检查 |
| format / format:write | prettier --check . / --write .；受 .prettierignore 排除规则约束 |

## 依赖按用途分组

react/react-dom 负责组件和 DOM 渲染；lucide-react 提供图标；react-markdown + remark-gfm 渲染安全 Markdown 及常见表格/列表语法。没有 Next.js、DeerFlow 包、全局状态库或前端模型 SDK，模型和私密配置留在后端。

开发依赖包括 TypeScript 和类型声明、Vite/React 插件、Vitest、Playwright、ESLint/TypeScript ESLint/React Hooks 插件、Prettier。带 ^ 的范围允许兼容版本解析，不能把这里写的 ^19.2.0 误报为实际已锁定 React 19.2.0。

本文件没有独立生产 start 命令；生产将 dist 交给 FastAPI 同源服务。smoke.mjs 需要明确给出测试后端地址，由项目验收脚本组织，不是这里的自动生命周期脚本。

相关说明：[锁文件实际版本](pnpm-lock.yaml.md)、[Vite 配置](vite.config.ts.md)、[浏览器配置](playwright.config.ts.md)、[真实联调脚本](scripts/smoke.mjs.md)。

