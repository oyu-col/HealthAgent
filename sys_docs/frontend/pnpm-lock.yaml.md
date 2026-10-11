# 依赖解析快照与可复现安装

- 对应源码：`frontend/pnpm-lock.yaml`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/pnpm-lock.yaml) · [本目录说明](README.md)

## 作用

这是 pnpm 的生成型依赖锁文件，当前 lockfileVersion 为 9.0。它不是应用运行逻辑，也不是要逐包手工维护的设计文档。package.json 声明“允许什么范围”，此文件记录“本次实际解析到了哪些版本、完整性信息及依赖关系”，使不同环境可以复现同一依赖图。

## 当前结构

- settings 中 autoInstallPeers=true，excludeLinksFromLockfile=false。
- importers 下的 "." 对应这个前端包，按 dependencies/devDependencies 记录 specifier 和 version。
- packages 保存包标识、resolution.integrity、engines、peerDependencies、平台条件等元信息。
- snapshots 保存解析后的依赖、可选依赖和 peer 组合关系。带括号的版本后缀描述 peer 解析上下文，不是人为命名的另一套 React 版本。

## 直接依赖的已锁定版本

| 组别 | 版本 |
|---|---|
| React / React DOM | 19.3.0 / 19.3.0 |
| lucide-react | 0.562.0 |
| react-markdown / remark-gfm | 10.1.0 / 4.0.1 |
| Vite / React 插件 | 8.3.2 / 6.1.1 |
| TypeScript / Vitest | 5.9.3 / 4.1.11 |
| Playwright Test | 1.63.0 |
| ESLint / @eslint/js | 9.39.5 / 9.39.5 |
| React Hooks ESLint / typescript-eslint | 7.1.1 / 8.71.0 |
| Prettier | 3.9.9 |
| @types/node / @types/react / @types/react-dom | 24.19.1 / 19.3.0 / 19.3.0 |

这些是读取当前锁文件得到的快照，不代表本次文档工作重新安装或验证了依赖，也不表示它们一定是最新版本。更新依赖时应通过 pnpm 重新生成并配合项目检查，不应只手工替换一个 version 而保留不匹配的 integrity 或 snapshots。

node_modules 是安装产物，不属于本镜像文档逐文件解释范围；锁文件本身属于项目依赖配置，所以保留此页说明。

相关说明：[依赖声明](package.json.md)、[忽略格式化锁文件](.prettierignore.md)。

