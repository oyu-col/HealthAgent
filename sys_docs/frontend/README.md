# 前端工程总览

- 对应目录：`frontend/`
- 核对日期：2026-10-04
- 阅读入口：[实际目录](../../frontend/) · [上级说明](../README.md)

## 运行职责与阅读路线

这是独立的 React + TypeScript + Vite 前端，负责用户输入、资源管理、流式反馈和执行记录展示。它复用现有 FastAPI 业务 API，不从浏览器直接调用模型、数据库或 DeerFlow。生产构建由后端同源提供；开发 Vite 转发 /api 与 /healthz 到 8000。

建议按 index.html → src/main.tsx → src/App.tsx → Chat/Records/Documents/Memory → src/lib/api.ts 阅读：先理解入口和身份生命周期，再理解业务状态和传输完整性。参考布局包括侧栏、居中消息区、圆角输入区、资料辅助面板，具体取舍见 [DeerFlow UI 参考记录说明](../docs/ui-deerflow-reference.md.md)。

## 边界与数据安全

页面 token 和健康资料只存在组件内存，换凭据卸载旧工作区。所有写入走真实 API，列表没有种入合成统计；合成数据仅用于测试和验收脚本。模型服务配置属于后端，本目录不存在用于嵌入供应商密钥的前端环境变量。

## 源码与生成物

src 是产品实现，tests 是离线契约测试，scripts 包含真实后端联调工具，public 当前为空。node_modules、dist、test-results 是依赖、构建与测试生成物，不逐文件镜像；本文档集仍解释产生它们的配置与脚本。本次为文档阅读和对应关系检查，未重跑应用测试。

## 对应文件和子目录

- [src/](src/README.md)：目录说明。
- [tests/](tests/README.md)：目录说明。
- [scripts/](scripts/README.md)：目录说明。
- [public/](public/README.md)：目录说明。
- [package.json](package.json.md)：前端包元数据、依赖与开发命令。
- [pnpm-lock.yaml](pnpm-lock.yaml.md)：依赖解析快照与可复现安装。
- [vite.config.ts](vite.config.ts.md)：Vite 开发代理与 Vitest 发现规则。
- [playwright.config.ts](playwright.config.ts.md)：Playwright 浏览器契约测试配置。
- [tsconfig.json](tsconfig.json.md)：TypeScript 编译和静态约束。
- [eslint.config.js](eslint.config.js.md)：ESLint 扁平配置与 React Hooks 规则。
- [.prettierignore](.prettierignore.md)：前端格式化工具排除清单。
- [index.html](index.html.md)：HTML 外壳与构建资产入口。
- [AGENTS.md](AGENTS.md.md)：前端开发约束及其在代码中的落点。

