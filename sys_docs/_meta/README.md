# 文档校验资料：覆盖、链接与阶段源码快照

核对日期：2026-10-11。本目录是 sys_docs 自身的校验资料，不对应运行时业务模块，不调用模型或读取私人数据库。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| [check-docs.mjs](check-docs.mjs) | 枚举源文件、匹配说明、验证本地链接、元数据、围栏与源码哈希 |
| [source-snapshot.json](source-snapshot.json) | 保留2026-10-04首次文档交付的原始源码快照，不覆盖 |
| [source-snapshot-phase-12.json](source-snapshot-phase-12.json) | Phase 11/12代码及说明审阅后建立的独立快照，默认检查基线 |
| [coverage.json](coverage.json) | 最近检查的真实结果，包含采用快照、文件/目录/链接数量与失败列表 |

根文件范围为.env、公开模板、.gitignore、AGENTS、README、规范；递归backend、frontend、docs、benchmark。包含手写源码、测试、锁文件、阶段报告和审阅后的benchmark/results。排除依赖、构建、缓存、smoke/benchmark临时目录、.pytest-tmp-*及benchmark/runs；data不在扫描入口。空目录仍要求目录说明。

.env只记录路径和说明映射，sha256=null、mode=schema-only-no-content-read；不读取内容或计算哈希。其他快照项只保存非秘密文件哈希和映射，不复制源数据。

## 如何使用

从HealthAgent根目录运行：

```powershell
node sys_docs/_meta/check-docs.mjs
node sys_docs/_meta/check-docs.mjs --index
```

默认对比Phase 12快照；--index额外刷新[文件索引](../文件索引.md)。源码增删改、缺少说明或损坏链接都会使检查失败。文件页必须包含正确“对应源码”路径和ISO格式核对日期，旧页可以保留实际审阅日期，不伪装所有文件本次都重新审阅。

未来确实变更代码并同步说明后，用新名称建立快照：

```powershell
node sys_docs/_meta/check-docs.mjs --snapshot-name source-snapshot-next-reviewed.json --snapshot --index
node sys_docs/_meta/check-docs.mjs --snapshot-name source-snapshot-next-reviewed.json
```

--snapshot-name限定为source-snapshot开头的简单JSON文件名，不能指向任意路径；--snapshot拒绝覆盖已有文件。原始快照不可通过覆盖来消除差异。只有经过审阅的源码变更和说明更新，才能建立新阶段快照；未改默认名时日常检查仍使用Phase 12基线。

## 检查范围与限制

检查逐文件/目录覆盖、源码指纹、清单增删、本地Markdown链接目标、UTF-8替换字符、代码围栏配对和冲突标记。数量读取coverage.json，不在本页写死以免增加文件后失真。

脚本不验证锚点、外部链接、说明的语义准确性，也不执行应用测试或评测模型。Phase 11/12后端、前端和Benchmark另有[真实验收记录](../../docs/phase-11-12-validation.json)。原2026-10-04“只编写文档”的历史范围不等于本次任务范围；旧阶段业务验收文件继续保留原样。
