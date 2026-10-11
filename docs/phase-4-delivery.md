# Phase 4 — Streaming

## Completed

LangGraph 原生 messages / values / custom 流 → FastAPI SSE → Python 增量客户端已完成。支持文本增量、工具开始 / 完成、执行完成 / 失败及 thread / request 标识。

## Files Changed

新增 `api/stream.py`、`api/sse.py`、`scripts/stream_client.py` 和 `tests/integration/test_streaming.py`；runtime 抽取共用异常与超时边界，工具 middleware 发出脱敏 custom 事件。

## Design

使用公开 `astream(version="v2")` 的统一 StreamPart；既有 `ainvoke(version="v1")` 保持 dict 返回。values 仅供服务端提取最终回答，不发原始状态。SSE 协议 v1 有递增 seq；完成事件中的 answer 为权威结果。工具事件不含参数和健康结果全文，只含工具标识、成功状态和错误码。取消时关闭图异步生成器并释放会话占用，checkpoint 可通过 Phase 3 接口继续。

## DeerFlow Reference

阅读 `runtime/stream_modes.py`、`runtime/runs/worker.py` 的 astream / close 生命周期，以及 Gateway `services.py` 的 SSE framing。借鉴事件转换与生成器关闭，独立实现小型单消费者协议，没有复制 LangGraph Platform 的全部 HTTP 协议或事件总线。接口依据 [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming) 核对。

## Tests

2026-10-03：完整离线测试 **83 passed / 1 skipped**，14.67 秒。覆盖真实图的逐片中文输出、单字节 UTF-8 传输解析、工具事件、最终回答与 checkpoint 一致、异常终止、取消模型与释放会话。

## Known Issues

SSE 无持久事件重放和 Last-Event-ID 恢复；断线后用 request_id 继续执行 / 取最终结果。HTTP 流建立后发生的错误以 run.failed 事件返回，客户端不能仅依据 200 判断成功。前端尚属 Phase 9，本阶段交付可运行测试客户端。fake 默认模型仅回显，不代表真实 provider token 延迟。

## Next Phase

Phase 5：文档摄取、切分、embedding、持久向量检索和可追溯证据。
