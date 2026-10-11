# UI 参考记录：从 DeerFlow 交互到独立工作台

- 对应源码：`docs/ui-deerflow-reference.md`
- 核对日期：2026-10-04
- 目录导航：[docs](README.md)
- 原文件：[ui-deerflow-reference.md](../../docs/ui-deerflow-reference.md)

原文核对日期为 2026-10-03，列出 DeerFlow 工作台、侧栏、会话列表、欢迎页、消息区、输入框、threads hooks、离线提示、文档/引用、Memory 设置和样式的真实源码位置及独立借鉴方式。

视觉上借鉴暖白、浅边框、统一 CSS token、限宽阅读区、左栏与圆角输入框；功能上关注 IME 输入、停止入口、加载/空/错误分支、移动端可达性和真实数据刷新。HealthAgent 不复制数千行组件、模型/插件管理、沙箱、任意 Artifact 编辑或账号系统。

流状态章节是重要契约说明：发送前保留 request_id，delta 仅为临时展示，completed.answer 为最终答案，断线/停止后读取服务端状态，can_resume 决定恢复资格，不能仅靠 pending 或创建新 request_id 重跑写入。文档和偏好也必须从真实 API 获取，不展示虚构“健康数据”。

该文件明示它是参考分析，不单独证明 UI 已实现/验收；实际交付见 [Phase 9](phase-9-delivery.md.md)，当前组件解释见 [frontend](../frontend/README.md)。源码行号只定位当时参考版本，后续移动参考仓库时应同步维护引用说明。
