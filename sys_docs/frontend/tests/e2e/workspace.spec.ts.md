# 工作台的 Chromium 用户流程与布局测试

- 对应源码：`frontend/tests/e2e/workspace.spec.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/tests/e2e/workspace.spec.ts) · [本目录说明](README.md)

## 运行方式

文件使用 @playwright/test，并扩展 api fixture：为每个测试创建独立 MockApi、安装页面路由拦截，结束时检查 unexpected 为空，防止未声明接口意外落到真实后端。页面和 React 组件真实运行，返回数据全部合成。Vite 由 global-setup 管理，浏览器项目与默认地址来自 playwright.config.ts。

## 当前十个场景

| 用例 | 行为和关键断言 |
|---|---|
| Chinese SSE... | 发送中文问题，仅接纳最终答案；检查 UUID 请求 ID；刷新后可打开新会话及预置历史，切换时旧答案消失 |
| EOF without completion... | 不完整流不能出现最终答案；用户点击恢复；只提交过一次 stream，resume 复用完全相同 request_id |
| record form... | 空必填数值不发 POST；填写 67.3 后提交嵌套 record/request_id；时间是 Z ISO；列表刷新至少两次并显示结果 |
| failed document indexing... | 上传失败 PDF 显示索引失败、询问禁用且无成功通知；成功 Markdown 显示就绪；询问仅填草稿，不自动 chat |
| a note with no index... | 新建文本笔记索引失败后仍禁用提问并显示错误，不声称建立索引成功 |
| memory is saved... | PUT 载荷仅含 value；首次点忘记不发 DELETE，确认后才删除并展示尚未设置 |
| changing credentials... | 401 连接界面输入合成 Alice token，再换 Bob；旧线程与消息消失；localStorage/sessionStorage 均为空 |
| narrow screens... | 390×844 打开抽屉进入记录页，打开添加表单；document.scrollWidth 不超过视口 |
| trace details... | 未知耗时/计数显示破折号、usage 不完整与终止原因空值明确说明；失败事件红点且有失败文字；Escape 关闭 |
| desktop and mobile... | 1440×1000 与 390×844 截图记录欢迎、Trace、记录视图；导航 aria-expanded 和无溢出断言 |

Trace GET 次数允许 1–2 次，是开发 StrictMode 可能重复挂载 effect 的正常情况，不能机械当作业务重复执行。

## 截图和可证明范围

主动截图写入 test-results/ui-review：desktop-welcome.png、desktop-trace.png、mobile-welcome.png、mobile-records.png。它们用于人工视觉检查，没有 toHaveScreenshot 基线比对，因此不是像素差异自动回归测试。

标题中“idempotent record”体现提交 request_id 契约，但该用例只断言单次 POST 形状及刷新，MockApi 不实现真实 SQL 去重；幂等保障需以后端测试为准。“persisted threads”在这里指 mock 状态跨 page.reload 保留，真实磁盘持久化由真实 smoke 覆盖。当前无供应商模型质量评测，无真实 OCR 或向量召回验证。本次文档工作未重跑用例。

相关说明：[MockApi 实现](mock-api.ts.md)、[启动清理](global-setup.ts.md)、[Playwright 配置](../../playwright.config.ts.md)、[真实后端路径](../../scripts/smoke.mjs.md)。

