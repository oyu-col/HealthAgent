# Phase 2 交付记录：Tool Runtime

- 对应源码：`docs/phase-2-delivery.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-2-delivery.md](../../docs/phase-2-delivery.md)
- 资料性质：2026-10-03 阶段历史记录；本文没有重新执行其中测试。

## 文件作用与交付内容

建立五类数据模型、SQLite、领域输入校验、统一 ToolResult、健康 Service/Repository 和首批八个工具；第九个 search_health_knowledge 到 Phase 5 才接入。

原文按规范七段式保存完成范围、受影响文件、设计、DeerFlow 参考、实际测试、限制和下一阶段，便于追溯这项能力为何进入工程。

## 应重点理解的设计

工具通过隐藏 ToolRuntime context 取得 owner，校验带时区时间和指标单位；记录与幂等回执同事务提交，查询受 owner 限定。参数错误变成安全 observation，框架控制信号继续传播。

## 历史验证怎样解读

当时首轮 75 passed / 1 skipped，覆盖真实图调用工具、SQLite 事实、ToolMessage、单位/时区、身份、隔离和重复写入。后续补充饮食/运动/趋势与并发幂等，汇总看 Phase 2–6 验收。

## 与当前代码的关系

fake 默认回显没有自然语言工具规划能力；local 是固定用户；首版没有删除/覆盖健康记录，create_all 不提供已有字段迁移。

继续阅读：[阶段汇总](phase-2-6-validation.json.md)、[现有健康工具](../backend/app/tools/health.py.md)。以后修改功能应更新当前源码说明与新的验收记录，不把本篇的历史通过数改写为未经执行的新结果。
