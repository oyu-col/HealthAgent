# 长期偏好的查看、修改与确认忘记

- 对应源码：`frontend/src/components/Memory.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/Memory.tsx) · [本目录说明](README.md)

## 定位

此处的 Memory 是可枚举的用户偏好，不是任意历史聊天、病历或健康指标的储藏区。组件接收 token/session，通过 `GET /api/memory` 获取 preferences 与 allowed_values。允许值来自后端，前端只负责中文显示，不能扩展用户可写字段。

## 固定四类偏好与标签

| key | 页面名称 | 当前标签覆盖值 |
|---|---|---|
| response_style | 回答风格 | concise 简洁明了；detailed 详细解释 |
| language | 交流语言 | zh 中文；en 英文 |
| diet_preference | 饮食偏好 | light 清淡、vegetarian 素食、no_spicy 不辣 |
| exercise_preference | 运动偏好 | walking、running、swimming、cycling、yoga |

`preferenceLabels` 同时导出给 App 的资料侧栏，避免两处翻译不一致。枚举之外的字符串会回退显示原值。没有已保存值时明确显示“尚未设置”，不会擅自把第一项当作已记住的事实。

## 编辑和删除流程

点击卡片设置 editing key，并将 selected 初始化为已保存值，或该项 allowed_values 第一项。打开时重置 deleting/error。普通保存执行 `PUT /api/memory/{key}`，载荷仅为 `{value: selected}`。

已存在偏好才显示“忘记”。第一次点击仅令 deleting=true，弹窗变为确认说明，尚未请求服务端；“确认忘记”才执行 DELETE。同一弹窗的取消在确认页会先回到选择页，普通编辑页的取消才关闭。确认说明明确已有聊天和健康记录保留。

保存成功关闭弹窗、刷新资源并显示通知；失败仍保留当前界面与 error；busy 时限制关闭、取消及提交，卸载时取消 AbortController。删除调用不携带 JSON body，传输层同时支持服务端返回 204 的情况。

## memory_enabled 的含义

session.memory_enabled 只显示“对话记忆已开启/关闭”。关闭时说明自动提取和注入关闭，但用户仍可管理已有偏好；页面并未把管理按钮整体禁用。手动 PUT 与自然语言提取是两条入口，是否提取、怎样注入，由后端实施。

相关说明：[共享弹窗](ui.tsx.md)、[请求 Hook](../lib/hooks.ts.md)、[MemoryData 类型](../lib/types.ts.md)、[确认删除测试](../../tests/e2e/workspace.spec.ts.md)。

