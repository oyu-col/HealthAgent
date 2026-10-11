# Phase 8 交付记录：Reliability

- 对应源码：`docs/phase-8-delivery.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-8-delivery.md](../../docs/phase-8-delivery.md)
- 资料性质：2026-10-03 阶段历史记录；本文没有重新执行其中测试。

## 文件作用与交付内容

补齐只读瞬态失败重试、单次工具超时、跨 Lead/子图共享预算和有限紧急自述守卫，并接入 Trace 领域事件。

原文按规范七段式保存完成范围、受影响文件、设计、DeerFlow 参考、实际测试、限制和下一阶段，便于追溯这项能力为何进入工程。

## 应重点理解的设计

采用框架 ToolRetryMiddleware。明确的 timeout/连接/429/5xx/SQLite busy 可重试，参数/权限等永久错误不重试；写工具不自动重放，超时或存储结果不确定返回 write_outcome_unknown。工具尝试和 SDK 内部重试有不同计数。

## 历史验证怎样解读

历史相关三文件 51 passed，扩展回归 67 passed；包括 embedding ConnectError 后真实 SQLite/citation 恢复，以及缺参、写超时、取消、共享预算。紧急守卫验证跳过模型且 SSE/history/回放一致。

## 与当前代码的关系

小范围中文规则不是完整医疗分诊，不能保证改写或其他语言覆盖。重复三次同工具/参数/观测会停止；当前没有在其外再实现无限 re-plan。无有效终态且无待执行节点时 can_resume=false。

继续阅读：[最终验证汇总](phase-7-10-validation.json.md)、[当前可靠性中间件](../backend/app/agent/reliability.py.md)。以后修改功能应更新当前源码说明与新的验收记录，不把本篇的历史通过数改写为未经执行的新结果。
