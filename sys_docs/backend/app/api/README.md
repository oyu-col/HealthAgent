- 对应目录：`backend/app/api/`
- 核对日期：2026-10-04
- 实际目录：[api/](../../../../backend/app/api/)
- 上级说明：[目录说明](../README.md)

# HTTP 接口层

## 职责与设计目的

把浏览器/脚本的 HTTP 请求转换为受控的业务调用，统一请求模型、身份依赖和响应协议。API 不自行规划工具，不直接拼 SQL，也不从 body 获取 user_id 授权；依赖 app.state 中由 main.py lifespan 装配的服务和 Runtime。

## 模块关系与主要流程

普通对话走 chat → ThreadService.prepare → Runtime → ThreadService.complete；恢复由 threads 复用 chat.execute_chat。流式对话由 stream 拥有 SSE 生成器，底层调用相同的会话与 Runtime 能力。schemas 规范成功/失败与会话类型，sse 处理文本帧。
记录表单绕过模型，直接调用 HealthService；documents 调 KnowledgeService；memory 调 MemoryService；traces 只查询脱敏 Trace；session 返回可信身份和有限能力设置。健康探针位于 chat 模块，但不调用模型。

## 协议与状态边界

- HTTP 普通错误使用 main.py 的 ErrorResponse；流建立后的业务错误使用 run.failed。
- ToolResult 的 success 与 HTTP 状态不是同一层：尤其查询必须检查结果字段，不能见 200 就判业务成功。
- request_id 是业务去重/恢复标识，run_id/trace_id 是一次执行/追踪标识，thread_id 是持久对话标识。
- completed 要等业务回执收尾；流 EOF、停止、仅收到文字片段均不代表完成。
- 用户归属由认证和服务/Repository 联合保证，UUID 只是格式检查。

## 主要调用者和下游

React 工作台、scripts/stream_client.py 和测试客户端调用本目录。下游为 services、agent Runtime、domain schemas、RAG 校验和 persistence Trace 查询。所有路由由 main.py 集中 include_router。

## 阅读和修改顺序

先看 schemas、chat、threads，再看 stream/sse；之后按具体 UI 功能读 records/documents/memory/traces。新增接口应保持输入禁止不必要字段、数据访问 owner 过滤、错误消息脱敏。认证策略、全局异常处理和资源初始化不应复制进每个路由。

## 对应验证

test_api、test_threads、test_streaming 验证对话核心链；test_ui_api 验证记录/会话/静态入口；RAG、Memory、observability 集成测试分别验证真实下游行为。本目录不包含用户删除健康事实或普通用户发布公共知识的 API。

## 文件导航

- [__init__.py](__init__.py.md)：API 包入口。
- [schemas.py](schemas.py.md)：HTTP 对话协议与响应模型。
- [chat.py](chat.py.md)：普通对话入口与公共执行流程。
- [stream.py](stream.py.md)：对话 SSE 流式传输入口。
- [sse.py](sse.py.md)：SSE 编码与轻量测试客户端解码。
- [threads.py](threads.py.md)：会话管理与恢复 HTTP 接口。
- [session.py](session.py.md)：可信会话配置查询。
- [records.py](records.py.md)：健康记录表单的直接业务接口。
- [documents.py](documents.py.md)：私人健康文档上传与列表接口。
- [memory.py](memory.py.md)：显式长期偏好管理接口。
- [traces.py](traces.py.md)：执行 Trace 查询接口。

