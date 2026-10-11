# reference-snapshot.json：被引用参考文件的内容基线

- 对应源码：`docs/reference-snapshot.json`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[reference-snapshot.json](../../docs/reference-snapshot.json)

## 数据结构与用途

这是 Phase 0 保存的 DeerFlow 本地源码基线。顶层记录 schema_version、phase、recorded_at/local_date/timezone、reference_root、Git 状态、采集方法及 observed_lockfile_versions；files 数组逐项包含 path、sha256、bytes、lines。当前清单共 57 个参考文件。

它为源码分析里的路径、符号与行号提供内容身份。verify_delivery.py 按 reference_root 找原文件重新计算 hash，确认选定参考内容未被此次实现更改；规范副本另行逐字节比较。

## 正确理解证据

reference_root 是采集机器上的绝对目录，搬迁后需明确处理；git_commit=null 表示没有取得 Git 提交，不能把 hash 清单伪装成官方 release。observed_lockfile_versions 属于当时 DeerFlow 锁文件，不是 HealthAgent 当前安装版本，后者看 backend/uv.lock。

bytes/lines 有助于人工核对，不证明代码行为已经运行。57 项只覆盖清单，不是整个仓库的完整性审计。此 JSON 无用户健康输入或运行密钥，不应混入这些数据。

关联：[源码分析](phase-0-deerflow-analysis.md.md)、[verify_delivery.py](../backend/scripts/verify_delivery.py.md)。本次 sys_docs 自己的源码快照位于 [_meta](../_meta/README.md)，与该参考仓库基线是不同对象。
