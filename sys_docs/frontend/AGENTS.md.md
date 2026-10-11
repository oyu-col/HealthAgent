# 前端开发约束及其在代码中的落点

- 对应源码：`frontend/AGENTS.md`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../frontend/AGENTS.md) · [本目录说明](README.md)

## 文档作用

这是提供给后续开发者和编码 Agent 的前端约定，继承项目根 AGENTS.md。它不是用户配置，也不参与 React 编译运行。核心目标是保持独立实现、同源契约和对健康数据的清楚表达。

## 主要要求与实现对应

- DeerFlow 只作侧栏、消息、composer、辅助面板与错误恢复的参考；package.json 没有 DeerFlow 运行依赖。
- API 使用同源 /api；开发 Vite 代理、生产 FastAPI 静态资源提供相同契约，前端构建变量不容纳模型密钥。
- token、健康数据与消息只在页面内存；App 切换身份卸载工作区，子组件取消请求。
- 增量只用于显示，run.completed.answer 决定最终结果；Chat 保存 request_id 并走 checkpoint 恢复。
- Markdown 不执行原始 HTML，不自动加载外部图片；资料侧栏不伪装成本轮实际证据。
- 记录通过真实 API 读写；空白、加载、失败、未授权、取消和手机交互必须可用。
- 修改前端时执行适当 typecheck/lint/test/build 和浏览器验证；mock 是流程契约，不是模型质量评测。

这些要求解释了当前代码许多看似额外的取消逻辑、结果检查和错误状态。本次任务只新建说明文档，没有重新运行这些检查；不能把该文件列出的命令写成已执行结果。

相关说明：[App](src/App.tsx.md)、[API](src/lib/api.ts.md)、[Chat](src/components/Chat.tsx.md)、[测试目录](tests/README.md)。

