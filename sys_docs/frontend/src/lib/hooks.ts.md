# 资源读取 Hook 与时间、错误格式化

- 对应源码：`frontend/src/lib/hooks.ts`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/lib/hooks.ts) · [本目录说明](README.md)

## useResource<T>(path, token)

这个 Hook 适用于只读 JSON 资源，返回 path、data、loading、error、reload。它不替代写入操作，也不是具有多键长期缓存的请求库。

state 保存结果所属 path；version 是刷新计数；reload 用稳定的 useCallback 增加 version。effect 依赖 path/token/version，创建 AbortController 和 active 标志。开始读取时，同路径刷新可以暂时保留旧 data；切换路径则立即设为 null。渲染返回值也按 state.path 与当前 path 比较，从而不会在 effect 尚未执行的一帧中展示另一类资源。

请求成功或失败只有 active 时才更新状态。cleanup 先把 active=false，再中止网络，双重避免被替换请求写回；token 变化同样触发重读。上层 App 在身份切换时整体卸载工作区，是完整隔离的重要补充。path=null 时不发请求，返回适用于未选中资源的空状态。

错误只保存可读字符串，而没有保留 ApiError 状态对象；使用此 Hook 的页面一般提供本页重试，不会凭此自动触发全局登出。失败会清空 data，调用者根据 loading/error 决定显示旧数据还是加载提示。

## 三个工具函数

- errorMessage：Error 实例取 message，其余 unknown 回退到固定中文“操作未完成，请稍后重试。”，避免把任意对象直接输出。
- formatDate：用 Intl.DateTimeFormat("zh-CN") 显示月、日、小时、分钟，可指定工作区 timezone；不显示年份或秒。函数假定输入是有效日期，未内建无效日期兜底。
- localDateTime：从当前设备 Date 调整 timezone offset，返回 yyyy-MM-ddTHH:mm，以便填入 datetime-local。返回值本身不带时区，表单提交时负责转换 ISO。

相关说明：[API](api.ts.md)、[记录时间输入](../components/Records.tsx.md)、[App 身份卸载](../App.tsx.md)。

