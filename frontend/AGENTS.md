# HealthAgent UI

继承根 AGENTS.md。独立 React / TypeScript / Vite 应用，不依赖 DeerFlow。

- 借鉴 DeerFlow workspace 侧栏、消息区、composer、辅助面板与错误恢复交互，不复制其主体代码。
- API 只使用同源 /api；开发代理与生产 FastAPI 静态资源保持相同契约。不要把后端凭据写进前端构建变量。
- token、健康数据和会话内容只保留在页面内存；切换访问凭据时中止请求并卸载旧用户工作区，禁止旧响应污染新用户状态。
- 流增量用于显示，run.completed.answer 为最终结果；流断开不是成功。保存 request_id，使用现有 checkpoint 恢复。
- Markdown 不解析原始 HTML，不自动加载模型生成的远程图片。引用不得凭空生成可查看的证据。
- 健康记录通过真实 API 查看和添加，不使用伪造统计或持久 mock 数据充当用户记录。
- 维护空白、加载、失败、未授权、流取消、恢复和窄屏状态；交互按钮必须有实际行为和可访问名称。
- 验证 pnpm typecheck / lint / test / build，关键跨组件流程用浏览器验证。前端测试 mock 只能用合成数据，不能被描述成模型质量评测。
