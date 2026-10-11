# Phase 10 交付记录：Trace / Observability

- 对应源码：`docs/phase-10-delivery.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-10-delivery.md](../../docs/phase-10-delivery.md)
- 资料性质：2026-10-03 阶段历史记录；本文没有重新执行其中测试。

## 文件作用与交付内容

通过公开 AsyncCallbackHandler 和领域 hooks 记录模型/工具/委派/重试，保存到 execution_traces，提供 owner 隔离的列表与详情，并处理恢复、取消及缓存回放。

原文按规范七段式保存完成范围、受影响文件、设计、DeerFlow 参考、实际测试、限制和下一阶段，便于追溯这项能力为何进入工程。

## 应重点理解的设计

只持久化白名单元数据，开始先存 running，终态写入后返回权威答案；Trace 失败明确 trace_unavailable，但业务与 checkpoint 不回滚。token 按模型 run 去重，可补 late usage；总步骤=model_calls+tool_calls，不是图 super-step。

## 历史验证怎样解读

历史专项 44 passed；后续回执不可变及并发 Trace 保留上限复核先复现失败再修复，新增 8 项。最终全套结果在 Phase 7–10 JSON。所有数值是测试执行观察，不是在线质量评分。

## 与当前代码的关系

单次 400 事件、全局 1000/用户 250 条；不逐出运行中 Trace，容量不足拒绝新准入。崩溃可能只留下开始记录，重启标 interrupted，未知计数不填零；SDK 隐藏重试不可精确观察，也无运行中持续 flush。

继续阅读：[最终验证汇总](phase-7-10-validation.json.md)、[当前执行采集](../backend/app/observability/recorder.py.md)。以后修改功能应更新当前源码说明与新的验收记录，不把本篇的历史通过数改写为未经执行的新结果。
