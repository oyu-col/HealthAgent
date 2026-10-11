# ESLint 扁平配置与 React Hooks 规则

- 对应源码：`frontend/eslint.config.js`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/eslint.config.js) · [本目录说明](README.md)

## 规则组合

导入 @eslint/js、typescript-eslint 与 eslint-plugin-react-hooks，通过 tseslint.config 组合 JavaScript recommended 和 TypeScript recommended。针对 ts/tsx 注册 React Hooks 插件：rules-of-hooks 为 error，防止条件调用 Hook 等错误；exhaustive-deps 为 warn，提醒 effect/useCallback 依赖遗漏。

本配置未启用所有可能的 React Compiler 或类型驱动 ESLint 规则，也没有把依赖告警全部提升为错误；阅读检查结果时应按实际等级解释。

## 排除与作用边界

忽略 dist、node_modules、test-results、playwright-report；package.json 中 lint 命令只指定 src tests，所以 scripts/smoke.mjs 和顶层配置文件不会被该命令自动检查。代码排版由 Prettier 负责，TypeScript 结构约束由 tsc 负责，三者不是同一种检查。

修改 Hook 清理或依赖列表时，要理解它为什么读取 active/alive ref，不能只为消除警告随意添加导致循环请求的依赖。

相关说明：[TypeScript](tsconfig.json.md)、[资源 Hook](src/lib/hooks.ts.md)、[包脚本](package.json.md)。

