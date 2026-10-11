# 私人文档上传、笔记创建与提问草稿

- 对应源码：`frontend/src/components/Documents.tsx`
- 核对日期：2026-10-04
- 阅读入口：[实际源码](../../../../frontend/src/components/Documents.tsx) · [本目录说明](README.md)

## 页面职责

管理当前用户可见的私人文档元数据，区分文件上传成功、文本解析成功、向量索引可用三个概念。输入为 token、session 和 onAsk(text) 回调。此页不会显示全文、下载原文件、删除文档、执行 OCR 或直接验证模型引用。

## 列表及上传

列表通过 `GET /api/documents` 读取 documents。resource 控制加载和列表错误；busy/dragging 分别控制上传状态和拖拽样式；error/notice 分别呈现失败及成功；textOpen 控制笔记弹窗。

文件选择框和拖拽都调用 upload。一次仅处理 files[0]；只允许 .txt/.md/.pdf 后缀、非空且不大于 2 MiB。客户端后缀判断不是内容安全校验，服务端仍需解析和验证。文件作为 FormData 的 file 字段发送到 `POST /api/documents/upload`；传输层由浏览器生成 multipart boundary。

响应返回 HealthDocument 后立即刷新列表。只有 index_status=indexed 才显示“已就绪”；否则保留失败提示。parse_status=failed 时提示可提取文字要求及扫描/加密 PDF 限制；其他索引失败提示重新上传同一文件重试。finally 清理 busy 并清空 input.value，使同一个文件可以再次被选择。组件卸载取消上传请求。

## 状态如何映射到交互

每行显示文件名、类型、工作区时区的创建时间与“私人资料”。index_status=indexed 显示可检索，pending 显示待处理，其余显示未就绪。error_code 存在时追加解析或索引提示。只有 indexed 文档开放“询问文档”按钮。

点击询问时，回调内容形如“请检索我的文档「文件名」，帮我整理主要信息并标注原文出处”。父级将它填入新对话草稿。这里没有发送 chat 请求，也没有用文件名代替后端的访问范围过滤。

## NoteForm：文本导入

笔记名称必填且最长 180 字符；没有 .txt/.md 后缀时追加 .md。正文必填、最多 200000 字符。发送 `POST /api/documents/text`，体为 `{filename, text}`，成功由父级刷新列表、关闭弹窗并根据 index_status 选择提示。

保存中不允许关闭；失败保留弹窗、文字与错误信息；卸载中止请求。笔记是供检索的非结构化材料，不会自动把其中提到的体重变成结构化记录，页面也明确指引使用健康记录功能。

相关说明：[App 的草稿导航](../App.tsx.md)、[HealthDocument 类型](../lib/types.ts.md)、[FormData 请求规则](../lib/api.ts.md)、[索引失败浏览器测试](../../tests/e2e/workspace.spec.ts.md)。

