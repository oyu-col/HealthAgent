# test_ui_api.py：工作台所依赖的后端接口契约

- 对应源码：`backend/tests/integration/test_ui_api.py`
- 核对日期：2026-10-11
- 阅读：[源码](../../../../backend/tests/integration/test_ui_api.py) · [测试目录](README.md)

## 定位

此文件验证 React 工作台依赖的后端行为：表单健康记录、连接身份、静态构建资源和会话标题/恢复状态。它使用 create_app、httpx.ASGITransport、临时 SQLite 和注入模型；没有启动浏览器，不能把通过本文件等同于完成 UI 布局或交互验收。

RECORDS 保存 metric/diet/exercise 三类合成输入；EmptyAnswerModel 返回空 AIMessage，用于验证无效终态不可恢复。

## 健康表单接口

test_records_api_writes_idempotently_and_filters_owner 对三个 kind 参数化。匿名 GET 401；Alice POST 嵌套 record+UUID request_id 成功，重复 POST JSON 完全相同，结果不含 user_id，列表一条且 truncated=false；沿相同 request_id 改内容返回 409/idempotency_conflict。Bob token 即使带 X-User-ID=alice 仍读不到 Alice，但可用同请求标识创建属于自己的不同 id 记录。

test_records_query_contract_and_strict_kind_validation 插入三天数据，按 start/type/limit=1 查询应最新时间正确且 truncated=true。无时区时间、limit=201、额外 user_id、逆序范围、记录类型不匹配、record/body 内多余身份、非 UUID、未知 kind、diet 查询夹带 metric_type 都返回 422，SECRET 不进入错误文本。

test_records_http_concurrent_retries_share_one_transaction_receipt 同 body 4 路并发写 metric，均 200 且同 id，最终一条。沿该 request_id 写 diet 返回 409 且 diet 列表为空，证明请求键跨表单 kind 一致约束。

## 身份与静态文件

test_session_returns_only_authorized_capabilities 断言匿名 401，正确 token 只返回可信 user_id、fake 模式、Asia/Shanghai、memory_enabled=false，响应不含 token。

test_ui_assets_are_optional_and_do_not_shadow_api 使用临时 dist/index.html 和 assets/app.js：根路径和 assets 可访问；healthz.phase=12、Swagger /docs 正常。未知 API/路径、缺失资源和编码的目录穿越都 404，不能回退为 index.html；dist 不存在时根路径 404。它只验证静态路由，不编译真实前端资源。阶段值检查用于保持当前后端探针与前端托管路径的契约一致，并不代表执行了 Phase 11/12 的评测。

## 会话标题与恢复

- test_thread_metadata_title_and_recovery_when_checkpoint_is_finished：新会话 title=新对话、idle、不可恢复；故障注入使图完成后回执失败。此时 pending=false 但 failed/can_resume=true，active_request_id 正确，标题归一空白、去 U+202E 控制字符且 ≤48 字符。恢复不新增模型调用，最终两条消息、idle；追加新问题也不改变首次标题。
- test_thread_metadata_distinguishes_running_and_interrupted_before_checkpoint：进入 prepare 但尚未运行图时 running、pending=false、messages=[]，退出后 interrupted/can_resume=true，用回执原文作为标题；resume 后真正执行并回到 idle。
- test_invalid_terminal_checkpoint_is_not_advertised_as_resumable：空答案使 chat 502；状态 failed、pending=false、can_resume=false，只有用户消息；resume 返回 409/resume_unavailable，模型只被调用一次。

## 关联与注意事项

关键实现见 [ThreadService](../../app/services/threads.py.md)、[HealthService](../../app/services/health.py.md)、[健康 Repository](../../app/persistence/health_repository.py.md)；HTTP 参数与静态路由在 api 和 main.py。前端判断恢复必须读取 can_resume，而非自行把 pending 当成唯一依据。

所有 fixture 为合成数据和测试凭据。本文不包含本机 .env 密钥，不宣称真实 provider 或浏览器效果；本文解释当前断言范围，具体执行结果应查看对应阶段的验证记录。
