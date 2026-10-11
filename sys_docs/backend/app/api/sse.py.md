- 对应源码：`backend/app/api/sse.py`
- 核对日期：2026-10-04
- 阅读源码：[sse.py](../../../../backend/app/api/sse.py)
- 所属目录：[目录说明](README.md)

# SSE 编码与轻量测试客户端解码

## 定位与设计目的

提供与业务执行分离的纯协议辅助函数：服务端使用 `encode_event`，测试与命令行客户端使用 `SSEDecoder`。浏览器的生产解析器在前端 api.ts，不能把这个类误认为前端正在运行的实现。

## 关键行为

- `encode_event(event, data)` 以 ensure_ascii=False 序列化 JSON，输出 event、id、data 三行和空行分隔符。id 为 run_id:seq；data 中必须已有 run_id 和 seq，否则会触发键错误。
- `SSEDecoder.__init__` 创建 UTF-8 增量解码器和文本缓冲区。
- `feed(chunk: bytes)` 接受任意网络字节块；保留未完成 UTF-8 字节与未结束帧，将 CRLF 归一为 LF，再按双换行拆帧。
- 每帧仅识别 event、id、data；多行 data 合并后执行 JSON 解析，返回已完整解码的事件列表。

## 输入输出与能力边界

feed 返回列表，可能为空或包含多帧；尚不完整的尾部继续保存在实例中。该类不校验协议 version、递增序号、执行 ID 或终态事件，也没有 EOF 完整性检查与缓冲大小上限。非法 JSON 会直接抛出解析错误。需要这些安全约束的生产客户端应使用更完整的前端实现。

## 验证与修改注意

test_streaming 将响应拆成单字节输入，验证中文多字节字符不会破坏；provider transport 测试也用此类观察后端 SSE。若扩展服务端帧格式，应检查脚本消费者和两个解析器，不能只改这里。

## 相关源码说明

- [backend/app/api/stream.py](stream.py.md)
- [backend/tests/integration/test_streaming.py](../../tests/integration/test_streaming.py.md)
- [backend/tests/integration/test_provider_transport.py](../../tests/integration/test_provider_transport.py.md)
- [frontend/src/lib/api.ts](../../../frontend/src/lib/api.ts.md)

