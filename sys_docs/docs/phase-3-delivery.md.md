# Phase 3 交付记录：Thread / Checkpoint

- 对应源码：`docs/phase-3-delivery.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-3-delivery.md](../../docs/phase-3-delivery.md)
- 资料性质：2026-10-03 阶段历史记录；本文没有重新执行其中测试。

## 文件作用与交付内容

完成会话创建、列表、归属、历史、继续对话、逻辑请求幂等和失败恢复；重启后读取历史并恢复待执行节点。

原文按规范七段式保存完成范围、受影响文件、设计、DeerFlow 参考、实际测试、限制和下一阶段，便于追溯这项能力为何进入工程。

## 应重点理解的设计

应用的 ThreadRecord/ChatRun 管 owner 和请求回执，官方 AsyncSqliteSaver 管 checkpoints.db。request_id 关联 HumanMessage 与工具操作，同请求变内容返回 409；有 checkpoint 时用 ainvoke(None)，尚未建立初始 checkpoint 时重送原输入。

## 历史验证怎样解读

历史完整离线测试 79 passed / 1 skipped，包含多轮、重建应用、跨用户 404、同 thread 并发 409，以及工具写入后模型失败再恢复仍只有一条记录。

## 与当前代码的关系

并发准入是进程内，仍要求 workers=1。这是原生 checkpoint 恢复，不是人工审批 interrupt UI；当前 can_resume 规则在后续可靠性与 UI 阶段进一步明确。

继续阅读：[阶段汇总](phase-2-6-validation.json.md)、[当前会话服务](../backend/app/services/threads.py.md)。以后修改功能应更新当前源码说明与新的验收记录，不把本篇的历史通过数改写为未经执行的新结果。
