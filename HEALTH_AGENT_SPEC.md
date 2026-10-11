# HealthAgent 项目开发规范

> 用途：放在 HealthAgent 工作目录根目录，供 Codex / ChatGPT / 其他编码 Agent 在持续开发过程中读取。  
> 本文件是项目级长期约束，不是一次性 Prompt。  
> 项目目标：**参考 DeerFlow 的成熟 Agent 架构与源码设计，基于 LangGraph / LangChain 独立实现一个健康垂域 Agent 应用。**

---

# 1. 项目定位

项目名称：**HealthAgent**

HealthAgent 是一个**独立项目**。

它：

- 不以 DeerFlow 作为运行时依赖；
- 不直接复用 DeerFlow 的 backend / frontend 代码作为项目主体；
- 不通过 `from deerflow...` 的方式调用 DeerFlow Runtime；
- 不以“fork DeerFlow 后修改”为主要开发方式。

它应该：

- 参考 DeerFlow 在 Agent Runtime、Tool、Memory、SubAgent、Streaming、Thread、Skill、FastAPI 和前端组织上的设计；
- 使用 **LangGraph / LangChain** 作为 Agent 核心框架；
- 根据健康管理场景重新设计并实现一套更精简、可理解、可测试、可评测的 Agent 应用。

关系如下：

```text
               DeerFlow
                  │
          阅读源码 / 参考设计
                  │
                  ↓
    ┌──────────────────────────┐
    │        HealthAgent       │
    │        独立项目           │
    │                          │
    │ LangGraph / LangChain    │
    │ FastAPI                  │
    │ React / Next.js          │
    │ SQLite / PostgreSQL      │
    │ Vector Store             │
    └──────────────────────────┘
```

---

# 2. 最终目标

HealthAgent 不应只是：

```text
User
  ↓
LLM
  ↓
Answer
```

而应形成可执行的 Agent 闭环：

```text
User Goal
   ↓
Intent / Goal Understanding
   ↓
Plan / Decision
   ↓
Action
   ↓
Tool / RAG / SubAgent
   ↓
Observation
   ↓
Evaluate
   ↓
Success?
   ├── Yes → Final Answer
   └── No  → Retry / Re-plan
```

最终希望具备：

- LangGraph / LangChain Agent
- Tool Calling
- Tool Registry / Executor
- RAG
- Long-term Memory
- Multi-Agent / SubAgent
- Thread / Checkpoint
- Streaming
- FastAPI Backend
- Web Frontend
- Health Domain Service
- SQLite / PostgreSQL
- Retry / Timeout
- Loop Protection
- Guardrail
- Trace / Logging
- Benchmark / Evaluation
- Failure Analysis

---

# 3. 核心原则

## 3.1 DeerFlow 是参考项目，不是依赖

任何模块开发前，可以先研究 DeerFlow 对应实现，例如：

```text
DeerFlow Lead Agent
→ 参考 Agent 构建方式

DeerFlow Tool Runtime
→ 参考 Tool 注册 / 执行方式

DeerFlow Memory
→ 参考长期记忆注入方式

DeerFlow SubAgent
→ 参考委派与上下文隔离

DeerFlow Streaming
→ 参考 LangGraph → SSE → Frontend 链路
```

然后在 HealthAgent 中重新基于 LangGraph / LangChain 实现。

禁止因为实现方便直接将 HealthAgent 变成 DeerFlow 二次开发项目。

---

## 3.2 不重复造 LangGraph / LangChain 已有能力

独立项目不意味着手写所有底层能力。

例如：

```text
Agent execution
State
Graph
Checkpoint
Streaming
Tool Calling
Middleware
```

如果 LangGraph / LangChain 已经提供成熟实现，应优先使用。

不要为了“自主实现”重新手写一个低质量的：

```python
while True:
    response = llm(...)
    ...
```

替代 LangGraph。

正确原则：

> 自己实现 Agent 应用架构与垂域逻辑，但底层 Agent Framework 使用 LangGraph / LangChain。

---

## 3.3 先理解，再编码

每开发一个重要模块，应：

1. 阅读 DeerFlow 对应模块；
2. 理解其职责、调用链和设计原因；
3. 判断 HealthAgent 是否需要完整复现；
4. 只保留 HealthAgent 真正需要的部分；
5. 使用 LangGraph / LangChain 实现自己的版本。

不要机械复制 DeerFlow。

---

## 3.4 每一个模块必须能够解释

项目最终必须达到：

```text
代码能运行
+
自己能讲明白
+
能测试
+
能评测
```

如果某个复杂设计无法解释其存在意义，则优先简化。

---

# 4. 技术栈

推荐：

## Agent

```text
Python
LangGraph
LangChain
```

## Backend

```text
FastAPI
Pydantic
SQLAlchemy
```

## Storage

第一阶段：

```text
SQLite
```

后续：

```text
PostgreSQL
```

## RAG

根据当前 LangChain 生态选择简单可靠方案：

```text
Document Loader
Text Splitter
Embedding
Vector Store
Retriever
```

优先本地可运行。

## Frontend

推荐：

```text
React / Next.js
TypeScript
```

无需完全复刻 DeerFlow UI。

## Streaming

```text
LangGraph Stream
↓
FastAPI
↓
SSE
↓
Frontend
```

---

# 5. 推荐总体架构

```text
                         Frontend
                            │
                            ↓
                         FastAPI
                            │
                            ↓
                     HealthAgent API
                            │
                            ↓
                    LangGraph Runtime
                            │
                     Health Lead Agent
                            │
          ┌─────────────────┼──────────────────┐
          ↓                 ↓                  ↓
        Tools              RAG              SubAgents
          │                                     │
          │                     ┌───────────────┼───────────────┐
          │                     ↓               ↓               ↓
          │               NutritionAgent   RecordAgent   ResearchAgent
          │
          ↓
   Health Domain Service
          │
          ↓
       Repository
          │
          ↓
 SQLite / PostgreSQL

同时：

LangGraph Runtime
├── Thread / Checkpoint
├── Context
├── Memory
├── Streaming
├── Retry / Re-plan
├── Guardrail
└── Trace
```

---

# 6. 推荐目录结构

项目初期可采用：

```text
HealthAgent/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── threads.py
│   │   │   ├── documents.py
│   │   │   └── health.py
│   │   │
│   │   ├── agents/
│   │   │   ├── lead_agent.py
│   │   │   ├── nutrition_agent.py
│   │   │   ├── record_agent.py
│   │   │   └── research_agent.py
│   │   │
│   │   ├── agent/
│   │   │   ├── state.py
│   │   │   ├── runtime.py
│   │   │   ├── context.py
│   │   │   ├── events.py
│   │   │   └── config.py
│   │   │
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── executor.py
│   │   │   ├── result.py
│   │   │   └── health/
│   │   │       ├── metrics.py
│   │   │       ├── diet.py
│   │   │       ├── exercise.py
│   │   │       └── documents.py
│   │   │
│   │   ├── health/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── repositories/
│   │   │
│   │   ├── rag/
│   │   │   ├── ingestion.py
│   │   │   ├── splitter.py
│   │   │   ├── embeddings.py
│   │   │   ├── vector_store.py
│   │   │   └── retriever.py
│   │   │
│   │   ├── memory/
│   │   │   ├── store.py
│   │   │   ├── extractor.py
│   │   │   ├── retriever.py
│   │   │   └── middleware.py
│   │   │
│   │   ├── skills/
│   │   │
│   │   ├── streaming/
│   │   │   └── sse.py
│   │   │
│   │   ├── guardrails/
│   │   │
│   │   └── tracing/
│   │
│   └── tests/
│
├── frontend/
│
├── benchmark/
│   ├── cases/
│   ├── graders/
│   ├── runner.py
│   └── report.py
│
├── docs/
│
├── HEALTH_AGENT_SPEC.md
└── README.md
```

这只是初始建议。

Codex 在真正创建目录前，应根据当前 LangGraph / LangChain API 和实际实现做适当调整。

---

# 7. DeerFlow 阅读目标

DeerFlow 不需要从头到尾完全复刻。

优先研究：

## 7.1 Agent / Runtime

重点回答：

```text
Lead Agent 如何创建？
使用了哪些 LangGraph / LangChain API？
State 如何保存？
一次 run 如何启动？
Agent 如何决定调用 Tool？
```

HealthAgent 要借鉴其思想，但实现自己的 Agent。

---

## 7.2 Tool

研究：

```text
Tool 如何定义
Tool 如何注册
Tool Schema 如何暴露给 LLM
Tool Call 如何执行
异常如何返回
```

HealthAgent 应有自己的 Tool 层。

---

## 7.3 Thread / State / Checkpoint

研究：

```text
thread_id
state
messages
checkpoint
resume
```

HealthAgent 使用 LangGraph Checkpointer 实现自己的会话状态管理。

---

## 7.4 Streaming

研究 DeerFlow：

```text
LangGraph
↓
Stream Event
↓
Backend
↓
SSE
↓
Frontend
```

然后实现 HealthAgent 自己的精简版链路。

---

## 7.5 Memory

研究：

```text
什么时候读取 Memory
如何注入 Context
什么时候提取长期信息
如何持久化
```

HealthAgent 自己实现 Memory Store / Middleware。

---

## 7.6 SubAgent

研究：

```text
Lead Agent 如何委派
SubAgent 如何注册
上下文如何隔离
结果如何返回 Lead Agent
```

然后使用 LangGraph / LangChain 实现 HealthAgent SubAgent。

---

## 7.7 Skills

研究 Skill 在 DeerFlow 中如何用于：

```text
工作流说明
领域规则
按需上下文注入
```

HealthAgent 可以设计自己的 Skill 系统，但应保持简单。

---

## 7.8 Frontend / Backend

研究：

```text
FastAPI 如何提供 Agent API
Streaming API 如何设计
Thread API 如何设计
Frontend 如何消费 Streaming Event
```

HealthAgent 重新实现自己的前后端。

---

# 8. Health Domain Layer

Agent 不应该直接负责底层业务数据访问。

保持：

```text
Agent
 ↓
Tool
 ↓
Service
 ↓
Repository
 ↓
Database / External API
```

---

# 9. 基础数据模型

第一版至少包含：

## UserProfile

```text
user_id
age
height
created_at
```

其他字段按需要增加。

不要为了展示功能过度收集敏感信息。

---

## HealthMetric

```text
id
user_id
metric_type
value
unit
measured_at
```

例如：

```text
weight
heart_rate
sleep_duration
steps
```

---

## DietRecord

```text
id
user_id
food_name
amount
meal_type
timestamp
nutrition_info
```

---

## ExerciseRecord

```text
id
user_id
exercise_type
duration
distance
calories
timestamp
```

---

## HealthDocument

```text
id
user_id
filename
document_type
created_at
parse_status
index_status
```

---

# 10. Tool System

第一版至少考虑：

```text
query_health_metrics
add_health_metric

query_diet_records
add_diet_record

query_exercise_records
add_exercise_record

query_health_documents

search_health_knowledge

calculate_health_trend
```

Tool 数量不追求多。

更重要的是：

```text
边界清楚
Schema 清晰
返回结构统一
可以测试
```

---

# 11. Tool Result

统一返回模型，例如：

```python
class ToolResult:
    success: bool
    data: object | None
    error_code: str | None
    error_message: str | None
    retryable: bool
```

不要出现：

```text
Tool A 返回 string
Tool B 返回 None
Tool C 直接抛未处理异常
```

---

# 12. Retry

必须区分：

## Tool Retry

因为临时环境异常，重新执行相同动作：

```text
timeout
429
5xx
connection reset
```

可以：

```text
limited retry
+
exponential backoff
+
jitter
```

---

## Agent Re-plan

当前策略本身无法完成目标。

例如：

```text
summary tool 数据不足
↓
Agent 判断
↓
改为查询原始记录
↓
调用分析 Tool
```

Tool Retry 与 Agent Re-plan 不得混为一谈。

---

# 13. Agent Loop Protection

Agent 必须有边界：

```text
max_steps
timeout
max_tool_calls
```

如果 LangGraph 已有合适机制，优先使用。

同时考虑检测：

```text
同一 Tool
+
同一参数
+
相同 / 无效 Observation
```

重复多次时停止或触发 Re-plan。

---

# 14. RAG

HealthAgent 应支持两个数据域。

## 14.1 Personal Health Documents

例如：

```text
体检报告
检查结果
个人健康文档
```

必须基于：

```text
user_id
```

做权限和检索隔离。

---

## 14.2 Public Health Knowledge

用于普通健康知识检索。

基本流程：

```text
Document
↓
Parse
↓
Chunk
↓
Embedding
↓
Vector Store
↓
Retriever
↓
Agent
```

第一版优先：

```text
简单
本地可运行
容易解释
```

不盲目追求复杂 RAG。

---

# 15. Memory

必须区分：

## Long-term Agent Memory

适合：

```text
用户偏好晚上运动
用户喜欢跑步
用户希望回答简洁
```

---

## Health Database

保存客观事实：

```text
体重
运动
饮食
检查记录
```

绝不能把重要健康记录仅存入自然语言 Memory。

---

# 16. Multi-Agent

建议：

```text
Health Lead Agent
├── NutritionAgent
├── RecordAgent
└── ResearchAgent
```

## Health Lead Agent

负责：

```text
Goal Understanding
Task Planning
Tool Selection
SubAgent Routing
Result Aggregation
Termination
```

## NutritionAgent

负责：

```text
Diet
Nutrition
Food-related analysis
```

## RecordAgent

负责：

```text
Health metrics
Historical records
Trend analysis
```

## ResearchAgent

负责：

```text
RAG
Public health knowledge
Evidence retrieval
```

原则：

> 不要为了“用了 Multi-Agent”而把简单任务复杂化。

例如：

```text
查询今天体重
```

直接：

```text
Lead Agent → Tool
```

即可。

---

# 17. Skill

Skill 用于表达：

```text
某种任务应该如何完成
```

Tool 表达：

```text
Agent 可以执行什么动作
```

第一版可设计：

```text
health-record-analysis
diet-analysis
health-trend-analysis
health-report
health-research
```

Skill 系统如果暂时没有明显收益，可以在基础 Agent 跑通后再实现。

---

# 18. Guardrail

HealthAgent 定位：

> 健康信息管理与健康知识辅助 Agent，不是医生。

要求：

1. 不做无依据的确定性诊断；
2. 数据不足时明确指出；
3. 不伪造医学来源；
4. 高风险情况建议寻求专业医疗帮助；
5. 私人健康数据必须用户隔离；
6. 删除 / 覆盖重要健康记录需要确认；
7. 不允许跨用户查询私人记录；
8. Tool 执行范围必须明确。

---

# 19. Thread / Checkpoint

使用 LangGraph 提供的 checkpoint / persistence 能力。

HealthAgent 自己维护：

```text
thread_id
user_id
metadata
```

目标：

```text
Thread
↓
LangGraph State
↓
Checkpointer
↓
SQLite / PostgreSQL
```

要求能够：

```text
创建会话
继续会话
恢复 State
```

---

# 20. Streaming

目标链路：

```text
LLM / LangGraph
      ↓
Stream Event
      ↓
HealthAgent Backend
      ↓
FastAPI SSE
      ↓
Frontend
      ↓
实时 UI 更新
```

重点掌握：

```text
astream / stream
event type
SSE
client consumption
```

第一版不要过度实现复杂 StreamBridge，除非实际出现断线、多订阅者等需求。

---

# 21. Trace / Observability

每次 Agent Task 尽量记录：

```text
trace_id
thread_id
task
agent_steps
tool_calls
tool_arguments
tool_results
subagent_calls
retry_count
total_steps
latency
token_usage
termination_reason
success / failure
```

注意避免不必要地记录敏感健康原文。

目标：

> 一个 Benchmark Case 失败时，可以从 Trace 中定位失败发生在哪一步。

---

# 22. Benchmark

项目必须建立自己的 HealthAgent Domain Benchmark。

第一版：

```text
20 ~ 30 cases
```

后续：

```text
100 ~ 150 cases
```

Case 类型：

```text
Single Tool Query
Write Operation
RAG
Multi-Tool
Multi-Agent
Missing Parameters
Ambiguous Input
Tool Failure
Tool Timeout
Recovery
Safety
Loop Detection
```

---

# 23. Benchmark Case 结构

建议：

```text
case_id
input
initial_environment
expected_state
expected_tool
forbidden_tool
expected_answer_constraints
grader
```

按任务类型可选字段。

---

# 24. Evaluation Metrics

至少：

```text
Task Success Rate
Tool Selection Accuracy
Tool Argument Accuracy
Tool Execution Success Rate
Recovery Rate
Loop Rate
Average Tool Calls
Average Agent Steps
Latency
```

RAG 可以增加：

```text
Retrieval Hit Rate
Grounded Answer Rate
```

只能使用真实运行结果。

禁止伪造提升指标。

---

# 25. Task Success 定义

不能因为 Agent 最终输出：

```text
操作成功
```

就判定成功。

---

## 写操作

例如：

```text
记录今天跑步 5 公里
```

应检查：

```text
DB record exists
exercise_type == running
distance == 5
date correct
```

---

## 查询任务

使用 Ground Truth。

---

## RAG

检查：

```text
关键事实
检索证据
Groundedness
```

---

## Multi-step

检查：

```text
Final Result
+
Environment State
+
必要关键步骤
```

---

# 26. Failure Analysis

失败分类至少包括：

```text
Tool Selection Error
Tool Argument Error
Tool Runtime Error
RAG Retrieval Error
Reasoning Error
SubAgent Routing Error
Loop
Early Stop
Safety Violation
```

---

# 27. Agent Development Loop

项目最终必须形成：

```text
Build
↓
Benchmark
↓
Trace
↓
Failure Analysis
↓
Optimization
↓
Benchmark Again
```

优化可能涉及：

```text
Prompt
Tool Description
Tool Schema
Context
RAG
Memory
Retry
SubAgent Routing
Skill
Guardrail
```

不能只用：

```text
感觉效果更好
```

作为优化依据。

---

# 28. 推荐开发阶段

## Phase 0 — DeerFlow Reference Analysis

目标：

**只研究 DeerFlow，不写 HealthAgent 大量业务代码。**

重点分析：

```text
Agent construction
Tool runtime
Thread / Checkpoint
Streaming
Memory
SubAgent
Skill
FastAPI
Frontend
```

输出：

```text
1. DeerFlow 对应模块真实源码位置
2. 每个模块职责
3. 关键调用链
4. 哪些设计值得 HealthAgent 借鉴
5. 哪些设计对 HealthAgent 过重，应简化
6. HealthAgent 最终架构方案
```

---

## Phase 1 — HealthAgent Skeleton

创建独立 HealthAgent 项目。

完成：

```text
Python project
FastAPI
LangGraph / LangChain
Config
Basic model client
Minimal Lead Agent
```

跑通：

```text
User
↓
Agent
↓
Answer
```

---

## Phase 2 — Tool Runtime

实现：

```text
Health Tools
Tool Schema
ToolResult
Validation
Service
Repository
SQLite
```

跑通第一个 Agent 闭环：

```text
User
↓
Agent
↓
Tool
↓
DB
↓
Observation
↓
Agent
↓
Answer
```

---

## Phase 3 — Thread / Checkpoint

实现：

```text
thread_id
LangGraph Checkpointer
resume
conversation state
```

---

## Phase 4 — Streaming

实现：

```text
LangGraph stream
↓
FastAPI SSE
↓
Frontend / test client
```

---

## Phase 5 — RAG

实现：

```text
ingestion
chunk
embedding
vector store
retriever
RAG Tool
```

---

## Phase 6 — Memory

实现：

```text
Memory extraction
Memory storage
Memory retrieval
Context injection
```

明确：

```text
Memory ≠ Health DB
```

---

## Phase 7 — Multi-Agent

实现：

```text
Lead Agent
NutritionAgent
RecordAgent
ResearchAgent
```

完成简单委派和结果汇总。

---

## Phase 8 — Reliability

加入：

```text
Retry
Timeout
Max Steps
Loop Detection
Guardrail
Structured Error
```

---

## Phase 9 — Frontend

实现自己的 HealthAgent UI。

至少：

```text
Chat
Thread
Streaming
Documents
Health Records
```

不要求复制 DeerFlow 全部 UI。

---

## Phase 10 — Trace / Observability

实现：

```text
trace
step
tool call
retry
latency
termination
```

---

## Phase 11 — Benchmark

先构建：

```text
20 ~ 30 cases
```

跑通完整评测。

---

## Phase 12 — Evaluation & Optimization

完成：

```text
Baseline
↓
Failure Analysis
↓
Optimization
↓
Benchmark Again
```

形成真实项目闭环。

---

# 29. 测试要求

至少包含：

## Unit Test

```text
Repository
Service
Tool
Validation
Retry
Memory
```

## Integration Test

```text
Agent → Tool → DB

Agent → RAG → Retriever
```

## Agent Evaluation

```text
Benchmark Runner
```

---

# 30. Codex 工作规则

每次执行较大任务前：

1. 阅读本文件；
2. 阅读当前项目 `README.md`；
3. 查看当前 Git 状态 / diff；
4. 阅读当前任务相关源码；
5. 不重复实现已有代码；
6. 不擅自扩大需求范围。

如果还需要参考 DeerFlow：

- 先定位 DeerFlow 对应模块；
- 说明参考了什么设计；
- 不直接把 DeerFlow 模块作为 HealthAgent 依赖。

---

# 31. 每个 Phase 的交付格式

每个阶段完成后必须给出：

## Completed

完成内容。

## Files Changed

新增 / 修改文件。

## Design

为什么这样设计。

## DeerFlow Reference

如果参考了 DeerFlow：

```text
参考模块
学习到的设计
HealthAgent 中如何简化 / 调整
```

## Tests

列出实际运行的测试。

明确区分：

```text
实际执行并通过
```

与：

```text
建议之后执行
```

禁止把未执行测试写成通过。

## Known Issues

当前问题。

## Next Phase

下一阶段。

---

# 32. 第一次使用本文件时的任务

如果当前 HealthAgent 尚未创建，第一次读取本文件时：

**只执行 Phase 0。**

请不要直接开始完整编码。

首先研究 DeerFlow 当前源码，重点定位并分析：

```text
Lead Agent
LangGraph / LangChain usage
Tool
Thread / State / Checkpoint
Streaming
Memory
SubAgent
Skill
FastAPI
Frontend
```

然后给出：

1. DeerFlow 当前真实目录与文件位置；
2. 用户请求从前端到 Agent 再返回前端的调用链；
3. 每个模块实际依赖 LangGraph / LangChain 的位置；
4. HealthAgent 可以直接使用哪些 LangGraph / LangChain 能力；
5. 哪些 DeerFlow 设计值得参考；
6. 哪些 DeerFlow 设计对本项目过重；
7. HealthAgent 独立项目的最终目录结构；
8. Phase 1 的具体实现计划。

完成后停止，不提前进入 Phase 1。

---

# 33. 项目的核心叙事

HealthAgent 最终应该能够被准确描述为：

> 基于 LangGraph / LangChain 构建的个人健康管理 Agent。项目参考 DeerFlow 等成熟 Agent 项目的架构设计，独立实现健康领域 Tool、RAG、长期 Memory、Multi-Agent 协作、Thread/Streaming、可靠性控制与 Domain Benchmark，并通过 Trace 与 Failure Analysis 建立可重复的 Agent 评测和优化闭环。

不要描述成：

> 基于 DeerFlow 二次开发。

因为 HealthAgent 是一个独立实现的项目，DeerFlow 是其重要的源码与架构参考。
