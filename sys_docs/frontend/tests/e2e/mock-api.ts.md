# 浏览器测试专用合成 API 和用户状态

- 对应源码：`frontend/tests/e2e/mock-api.ts`
- 核对日期：2026-10-11
- 阅读入口：[实际源码](../../../../frontend/tests/e2e/mock-api.ts) · [本目录说明](README.md)

## 文件定位

这是 E2E fixture 的后端替身，只被 workspace.spec.ts 使用，不会被生产 App 导入。常量 ALICE_TOKEN/BOB_TOKEN、UUID、日期、ANSWER、TRACE、RUN 都是明确合成数据，不是部署凭据。它通过 page.route 截获 **/api/** 与 /healthz，不启动 FastAPI、模型、SQL 或 embedding。

## 状态结构

owners 含 alice/bob 两套独立 OwnerData，各有 threads、三类 records、documents、memory。初始线程各含不同历史问答；偏好允许值与 UI 契约一致。nextId 生成可预测合成 ID。requests 记录请求方法、路径、JSON body 与 authorization，供测试断言；这些记录只存在测试进程内。unexpected 收集未声明接口，fixture 收尾必须检查为空。

requireAuth 默认 false，开启后只接受两个合成 Bearer 值；Bob token 选择 Bob 数据，否则默认 Alice。这里模拟用户分离，不能代替真实后端认证安全测试。

## 可控制的失败与返回路径

| 接口族 | 替身行为 |
|---|---|
| session / healthz | session 返回合成 user_id、fake 模式、Asia/Shanghai 与已启用 Memory；healthz 单独返回 status=ok、phase=12、model_mode=fake |
| threads | 列表、创建、详情保存在内存数组，未找到时 404 |
| chat/stream | 创建或查找线程、追加用户消息；输出 started、两段 delta；complete 模式追加 completed 与助手历史 |
| resume | 校验请求 ID 与 active_request_id 相同，清理 pending/can_resume，追加最终答案 |
| records | GET 返回 ToolResult，POST 直接把 record 加到数组并包 ToolResult |
| documents | GET 返回列表；upload 从 multipart 文本取文件名，text 从 JSON 取；由 ingestionStatus 控制成功或失败 |
| memory | GET 返回 preferences/allowed_values；PUT 替换键值，DELETE 移除 |
| traces | 返回预设 interrupted、未知统计、丢弃事件及一个失败工具事件，验证 UI 不补造零值 |

streamMode=incomplete 让流在没有 completed 时结束，用于恢复场景。ingestionStatus=failed 模拟解析失败，测试里“synthetic unreadable PDF”并没有真正交给 PDF 解析器。未识别请求返回 501 unexpected_test_request，而非悄悄联网。

healthz 的阶段号同步当前后端 HealthResponse，但仍是 Playwright route.fulfill 生成的合成响应。它不探测后端就绪、不启动 Benchmark，也不说明在线模型或 embedding 服务可用；真正的本地 HTTP 连接由 smoke 验证。

## 与真实协议的差距

这是最小 UI 契约替身，records GET 没有完整实现时间、指标筛选或 limit；POST 没有数据库唯一约束和持久幂等；上传不生成向量；线程 status 常用 completed 而真实服务空闲状态为 idle，UI 主要根据 can_resume 判断。模拟 stream 通过一次 route.fulfill 返回文本，真正跨 chunk UTF-8 解析由单元测试构造，真实网络 SSE 由 smoke 验证。

修改接口时应先对照后端 schema 更新替身，不能把测试方便返回的字段形状当成新的生产规范。

相关说明：[使用该替身的用例](workspace.spec.ts.md)、[传输单元测试](../unit/api.test.ts.md)、[真实 smoke](../../scripts/smoke.mjs.md)。

