# AGENTS.md：项目级持续开发约定

- 对应源码：`AGENTS.md`
- 核对日期：2026-10-11
- 目录导航：[本目录说明](README.md)
- 源码：[AGENTS.md](../AGENTS.md)

这份文件面向后续开发者和编码助手，约束如何推进 HealthAgent，不是供运行时模型读取的 system prompt，也不是业务 API 配置。它说明项目工程目前到 Phase 12，已形成29个案例和离线优化闭环，真实模型连接受阻仍待验收；要求按阶段输出可审查交付记录。

核心约定是：HealthAgent 独立运行，DeerFlow 只作只读参考；先定位真实源码，优先采用 LangChain/LangGraph 官方能力；保持 Tool→Service→Repository，服务端身份与 owner 过滤贯穿每次操作；区分 Thread、checkpoint、业务数据和偏好；保留取消、有限预算及真实失败语义。

文件同时强调输入/健康隐私、禁止虚构测试和模型效果、源码/文档同步，以及 Windows 运行验证的实际约束。后端与前端还有更具体的 [backend/AGENTS.md](backend/AGENTS.md.md)、[frontend/AGENTS.md](frontend/AGENTS.md.md)。

评测新增约定要求先冻结case/grader/protocol/settings并保存baseline，再改业务app；若评分器自身有误，先修正规则并重建基线，不能跨协议声称提升。真实provider使用显式allow-provider和合成数据；失败样本必须保留。阶段历史记录不得覆写为当前结果。

阅读它能理解“为什么不直接复制 DeerFlow 主体”“为什么不把 fake 回显宣称为医学能力”“为什么必须单独标记 live 跳过”等开发决定。修改该文件会影响以后工作的约束，但不会改变当前已启动服务；应避免把尚未实现的架构愿景写成已交付状态。
