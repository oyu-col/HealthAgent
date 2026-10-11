# verify_delivery.py：原阶段交付的静态一致性检查

- 对应源码：`backend/scripts/verify_delivery.py`
- 核对日期：2026-10-11
- 目录导航：[本目录说明](README.md)
- 源码：[verify_delivery.py](../../../backend/scripts/verify_delivery.py)

## 检查对象

脚本从自身位置定位项目根，读取 docs/reference-snapshot.json，其中 reference_root 指向被引用的 DeerFlow 本地目录。对清单中的文件重新计算 SHA-256 并比较；同时比较 HealthAgent 和参考目录中的 HEALTH_AGENT_SPEC.md 字节是否一致。

Markdown 链接检查范围是根 README.md、AGENTS.md 与 docs/*.md，跳过 URL scheme 和纯锚点，去掉 fragment 后检查本地目标是否存在。它并不遍历 sys_docs，也没有验证所有 Markdown 锚点、网页可达性或链接描述的语义。

阶段文档检查覆盖 Phase 0–12共13份，每份必须有 Completed、Files Changed、Design、DeerFlow Reference、Tests、Known Issues、Next Phase 七个标题。Phase 11/12新增两份只读DeerFlow参考源码哈希，并将benchmark/README及results/README纳入链接检查。结果以JSON输出；引用变化、规范不一致、坏链接或缺标题会使进程退出码为1。

## 证明范围

SHA-256 可证明被纳入清单的本地文件内容未变，不能代表整个参考仓库任意文件都未变，也不能替代 Git commit 标识。脚本不会执行应用、调用模型、检查 UI 或计算医学准确率。参考目录搬移后应正确处理基线引用，不能为了通过检查随意重写 hash。

新增源码说明采用 [_meta/check-docs.mjs](../../_meta/check-docs.mjs) 做独立覆盖/链接校验；两种检查的输入和证明范围不同。
