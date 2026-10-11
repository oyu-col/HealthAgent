# Phase 7–10 验证 JSON：当前交付的历史汇总

- 对应源码：`docs/phase-7-10-validation.json`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-7-10-validation.json](../../docs/phase-7-10-validation.json)

## 记录范围

这份 schema_version=1 的 JSON 对应 2026-10-03 Phase 7–10 汇总，保存 Windows/Python/Node/pnpm 环境、后端/前端/浏览器执行结果、静态参考一致性、修复后的最终检查及未执行边界。它是当前代码交付的历史证据，不是本次说明编写过程中新跑出的结果。

## 关键结果与含义

后端完整 pytest 为 155 passed / 1 skipped、36.03 秒，Ruff 与 83 个 Python 文件格式检查通过。前端 33 项单元测试、类型/Lint/格式/build 检查通过；合成 API 的 Chromium 用例为 10 passed。合成服务验证异常/身份/恢复分支，与真实后端测试分开统计。

真实 UI smoke 连接自有临时 Uvicorn/SQLite，使用构建后的页面与 fake 模型，记录 API/浏览器检查、1440×1000 桌面与 390×844 移动视图检查，以及服务端口关闭和临时数据清理。它能说明页面/数据库/协议联通，不能证明真实模型规划与医学质量。

静态部分记录 57 个参考文件未变、规范字节一致、91 个本地链接有效、阶段章节齐全。记录还提到本地演示配置从模板创建，未提供真实凭据。

## 阅读与维护

重点同时阅读 status、执行条件和 not_executed：真实 provider、真实 embedding 联调、Phase 11 Benchmark、Phase 12 优化仍未完成。UI 截图是当时目视验收记录，并非自动像素回归基线。

设计与限制见 [Phase 7](phase-7-delivery.md.md)、[Phase 8](phase-8-delivery.md.md)、[Phase 9](phase-9-delivery.md.md)、[Phase 10](phase-10-delivery.md.md)。本次文档覆盖统计单独写入 [_meta/coverage.json](../_meta/coverage.json)，不改变这份历史验收数据。
