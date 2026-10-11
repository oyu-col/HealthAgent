# test_memory.py：偏好保存、注入与忘记语义

- 对应源码：`backend/tests/integration/test_memory.py`
- 核对日期：2026-10-04
- 阅读：[源码](../../../../backend/tests/integration/test_memory.py) · [测试目录](README.md)

## 测试目的

通过真实应用 lifespan、临时 SQLite、SpyChatModel 与 HTTP API，检查偏好是否正确跨线程/重启保留，是否只以临时数据进入模型，以及旧请求回放会不会复活用户已经删除的偏好。模型可观察 messages，因此可以区分 SystemMessage、正常 HumanMessage 和临时偏好消息。

## 四个场景

### 显式保存与重启

test_explicit_preferences_persist_across_threads_and_restart 发送明确“清淡饮食”和“简短的回答”，GET /api/memory 得到 diet_preference=light、response_style=concise；来源 request_id 等于本次对话标识。关闭第一个 app，再用同一数据目录创建第二个 app，询问饮食计划。

断言模型消息中恰有一个名为 healthagent_preferences 的 HumanMessage，包含 light/concise；SystemMessage 不含 light；GET thread 的可见 messages 恰为两条，说明偏好注入没有写回 checkpoint。它没有断言模型回答风格变好，只验证注入位置和数据存在。

### 不应提取的内容

test_facts_quoted_instructions_and_negative_preferences_are_not_memories 逐项发送体重/血压事实、否定跑步、带引号文档引用和任意越权指令。请求可正常完成，但偏好列表保持空；PUT /api/memory/weight 返回 422，阻止把健康指标伪装为允许偏好。

### 更正、隔离、删除与回放

test_preference_correction_deletion_isolation_and_no_replay_resurrection 在 token 模式让 Alice 记住 running，再 PUT 为 swimming，Bob 查询为空；删除该 key 后，沿原 request_id 回放原“喜欢跑步”请求仍成功，但列表为空。关键是检查最终数据库状态，保证旧业务请求不能推翻后来的“忘记”。

该测试更正操作断言 HTTP 200，没有单独在更正之后、删除之前 GET 验证 swimming 值；说明应如实反映断言范围，不能把额外未写断言算成覆盖。

### 自动 Memory 关闭

test_memory_disabled_and_retrieval_relevance 用 memory_enabled=False 发送明确记忆句，GET 列表仍为空。尽管名称包含 retrieval_relevance，当前函数实际上只断言禁用自动提取，没有在此函数中测试关键词相关性筛选；后续需要扩大覆盖时应新增直接的相关性断言。

## 对应模块与维护

对应 [提取语法](../../app/memory/extraction.py.md)、[中间件](../../app/memory/middleware.py.md)、[服务](../../app/services/memory.py.md)、[Repository](../../app/persistence/memory_repository.py.md)。这些测试使用合成偏好，未调用真实模型，不是个性化效果 Benchmark。

更改偏好注入角色、删除回执或恢复流程时应保留临时 HumanMessage、owner 过滤、旧请求不复活三条核心不变量。本次文档工作没有重新运行测试。
