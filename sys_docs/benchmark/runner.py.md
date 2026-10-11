- 对应源码：`benchmark/runner.py`
- 核对日期：2026-10-11
- 阅读源码：[runner.py](../../benchmark/runner.py)
- 所属目录：[目录说明](README.md)

# 真实应用驱动、运行隔离和基准产物生成

## 设计定位

runner是评测的编排入口，负责构建和关闭应用、驱动HTTP请求、采集可核验证据、调用独立grader及保存报告。它复用app.main.create_app，既不直接向数据库写“期望答案”，也不重写Agent循环。

CLI预期从backend目录调用脚本。ROOT指向HealthAgent根，脚本把根目录加入sys.path以导入独立benchmark包；后端app依赖由backend执行环境提供。

## 每案例执行链路

1. run_case创建backend下唯一.benchmark-*临时目录，替代生产data_dir；以BASE_SETTINGS和有限case.settings构建Settings(_env_file=None)。
2. contract注入只带execution_plan且禁缓存的ContractModel；provider借助model_session取得真实客户端，设置temperature=0与max_tokens=1200。
3. AsyncExitStack拥有模型资源及FastAPI lifespan。应用创建实际SQL、checkpoint、工具、Memory和图后，seed通过Service准备合成数据。
4. 读取其他owner的初始快照；给runtime.graph_config追加Capture callback，保留原生产Trace callback。
5. 在单个应用的inject_fault作用域内，通过httpx.ASGITransport调用POST /api/chat；请求使用服务端固定benchmark-user身份与随机request_id。
6. replay在首轮成功后使用同一request_id/thread_id再请求；resume仅在首轮失败且有thread_id时调用线程恢复接口。模式支持resume，不表示当前所有恢复案例都使用该路径。
7. 从框架checkpoint补取Lead ToolMessage，再读SQL快照和实际持久Trace，verified_evidence核对真实chunk。
8. 组装内存observation交给grade_case，返回脱敏检查、失败分类、尝试状态、计数、文档key和Trace；退出lifespan后清理临时目录。

## 配置与外部访问边界

BASE_SETTINGS固定本机身份、Asia/Shanghai、local_hash 1024维、请求90秒、模型30秒、SDK重试0、工具调用12、图/模型预算16、子图步骤8、工具超时2秒、工具重试2。案例只能覆盖schema允许的执行项。

provider配置在清理环境前通过load_settings加载，只传递模型名、URL和SecretStr密钥到临时应用，不使用已有健康数据库。isolated_environment临时清除HEALTH_AGENT_/OPENAI_/LANGCHAIN_/LANGSMITH_环境并关闭外部tracing，finally恢复；这个进程级环境隔离应与当前串行运行方式配合，不宜直接并行化共享进程。

## 运行清单与指纹

run_suite先按profiles和--case-id选择；未知或模式不适用的显式case拒绝运行。provider必须有--allow-provider且配置模式为provider，不允许失败时静默退回fake。

manifest记录所选及profile排除案例、重复数、种子、Python、关键依赖版本、模型名、限制及以下指纹：

| 字段 | 覆盖内容 |
| --- | --- |
| case_digest | 校验并补默认值后的完整案例列表。 |
| grader_digest | graders目录下Python源码。 |
| protocol_digest | runner/model/environment/observation/report/schema六份协议源码。 |
| app_digest | 业务app内所有Python文件。 |
| settings_digest | 评测默认值、模型配置标识、endpoint散列、温度与输出预算。 |

服务URL不直接写入manifest。SHA-256用于标识本地代码内容，不等同Git提交或对远端模型版本的保证。

## 失败和报告持久化

每个案例外层220秒超时。未预料的异常转换为harness_error失败行，保留异常类型名而不保存原始消息；失败照常进入任务成功率分母。每完成一例先写report.tmp再替换report.json，避免整轮结束前完全没有结果。

全部运行结束才设置manifest.completed=true并生成Markdown；已有output目录拒绝覆盖。退出码0表示全通过，1表示含失败，2表示命令启动/配置失败。repeats限1到3；random.seed只影响本地随机源，不保证远端provider确定。

latency_ms从环境创建前开始，到读取/判分结束计时，包含准备开销；生产执行耗时来自trace.latency_ms。原始回答、参数和SQL内容用于内存判分，不进入返回报告。工具与模型错误只保留受限元信息。

## 验证与修改注意

[test_benchmark_runner](../backend/tests/integration/test_benchmark_runner.py.md)证明oracle修改不能改变模型决策、重放不重复落库、检索必须有实际索引证据，并检查临时目录回收。修改运行协议后必须重跑基线；不能只更改结果中的指纹。

