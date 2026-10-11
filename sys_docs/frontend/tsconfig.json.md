# TypeScript 编译和静态约束

- 对应源码：`frontend/tsconfig.json`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/tsconfig.json) · [本目录说明](README.md)

## 编译目标

target=ES2022，lib 包含 ES2022、DOM、DOM.Iterable，兼顾浏览器与现代语言 API；module=ESNext，moduleResolution=Bundler，与 Vite 解析方式配合。jsx=react-jsx 使用新 JSX 转换。useDefineForClassFields、isolatedModules 和 verbatimModuleSyntax 使模块及字段语义明确。

noEmit=true 表示 tsc 只检查，实际打包由 Vite 完成。allowImportingTsExtensions 与 resolveJsonModule 支持构建器可接受的源码导入形式。skipLibCheck 跳过第三方声明文件内部检查，减少外部声明噪声，不等于关闭应用自身类型检查。

## 严格性与覆盖范围

strict=true；noUnusedLocals、noUnusedParameters 和 noFallthroughCasesInSwitch 分别阻止无用局部项/参数及意外 switch 穿透。types 显式包含 vite/client 与 node：前者提供构建资产类型，后者为测试和配置提供 Node API 声明。

include 覆盖 src、tests、vite.config.ts、playwright.config.ts。scripts/smoke.mjs 是 JavaScript 文件，没有 allowJs，不在此 TypeScript 检查范围内。这里不做运行时 API schema 验证，也不检查 Python 后端。

相关说明：[构建命令](package.json.md)、[共享协议类型](src/lib/types.ts.md)、[ESLint](eslint.config.js.md)。

