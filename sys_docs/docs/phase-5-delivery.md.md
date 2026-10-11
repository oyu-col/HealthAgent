# Phase 5 交付记录：RAG

- 对应源码：`docs/phase-5-delivery.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[phase-5-delivery.md](../../docs/phase-5-delivery.md)
- 资料性质：2026-10-03 阶段历史记录；本文没有重新执行其中测试。

## 文件作用与交付内容

完成 TXT/MD/文本 PDF 解析、切分、embedding、SQLite 向量、Retriever、知识工具和引用元数据。私人上传与管理员公共资料导入分开。

原文按规范七段式保存完成范围、受影响文件、设计、DeerFlow 参考、实际测试、限制和下一阶段，便于追溯这项能力为何进入工程。

## 应重点理解的设计

RecursiveCharacterTextSplitter 每块上限 600、目标 overlap 80，保留页码/偏移。local_hash 是 1024 维词面基线；SQL 先按 owner/公共域与版本过滤，再计算相似度。索引状态与片段原子发布，失败可查与重试。

## 历史验证怎样解读

当时初轮 86 passed / 1 skipped；额外 11 项验证 SDK、真实文本 PDF、空白 PDF、embedding 失败隔离和重试。最终总数在 Phase 6 汇总，不应把子集加成独立总指标。

## 与当前代码的关系

无 OCR、无 ANN；接受文件限制 2 MiB/50 页/20 万字符/500 块，检索范围最多 5000 块。原文件不额外保存，换 embedding 需重新提供文件。真实神经 embedding 和医学资料质量未在线评测。

继续阅读：[阶段汇总](phase-2-6-validation.json.md)、[当前文档服务](../backend/app/services/knowledge.py.md)。以后修改功能应更新当前源码说明与新的验收记录，不把本篇的历史通过数改写为未经执行的新结果。
