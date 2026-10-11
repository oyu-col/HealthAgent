# Phase 1 验证 JSON：骨架阶段的实际执行摘要

- 对应源码：`docs/phase-1-validation.json`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-1-validation.json](../../docs/phase-1-validation.json)

原记录对应 2026-10-03 Phase 1，包含环境、锁定离线安装、pytest、Ruff、真实 HTTP smoke、静态检查及未执行范围。Python 3.12.10、Windows 是当时环境，不是配置文件给所有机器强制设定的版本。

当时完整 pytest 为 66 passed / 1 skipped、10.84 秒；Ruff 和锁定离线同步通过。smoke 在回环临时端口 50536 检查 healthz、OpenAPI、chat、trace header，并记录进程关闭。参考文件 57 项未变和规范字节一致属于独立静态检查。

skip 是真实 provider 需要显式启用，并非已经连接模型。该阶段范围还是独立的非流式骨架，没有后续数据库、工具、checkpoint、RAG 或 UI，因此不能拿此结果验收后续能力。

JSON 便于机器读取实际命令/状态/计数；设计原因看 [Phase 1 交付](phase-1-delivery.md.md)。以后重新测试应建立新结果并保留时间与条件，不直接将历史数字改成未经执行的推断。
