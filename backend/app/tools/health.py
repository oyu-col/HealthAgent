import hashlib
import json

from langchain.tools import ToolRuntime, tool

from app.agent.context import RunContext
from app.domain.schemas import DietInput, ExerciseInput, MetricInput, MetricType, QueryInput


def health_tools(service):
    async def add(kind, record, runtime):
        # Stable for duplicate proposals in one request, including different tool-call IDs.
        payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256((kind + payload).encode()).hexdigest()
        key = hashlib.sha256((runtime.context.operation_id + fingerprint).encode()).hexdigest()
        return (await service.add(kind, runtime.context.user_id, record, key)).model_dump(
            mode="json"
        )

    @tool
    async def add_health_metric(record: MetricInput, runtime: ToolRuntime[RunContext]) -> dict:
        """保存用户明确提供的健康指标；kg/bpm/hours/count，时间使用带时区 ISO8601。"""
        return await add("metric", record, runtime)

    @tool
    async def add_diet_record(record: DietInput, runtime: ToolRuntime[RunContext]) -> dict:
        """保存用户明确提供的饮食记录；不猜测食物量或营养值。"""
        return await add("diet", record, runtime)

    @tool
    async def add_exercise_record(record: ExerciseInput, runtime: ToolRuntime[RunContext]) -> dict:
        """保存用户提供的运动记录，时长分钟、距离公里，热量未知时留空。"""
        return await add("exercise", record, runtime)

    @tool
    async def query_health_metrics(
        runtime: ToolRuntime[RunContext], query: QueryInput | None = None
    ) -> dict:
        """读取当前用户的健康指标；可按类型和带时区起止时间筛选，truncated 表示还有数据。"""
        return (
            await service.query("metric", runtime.context.user_id, query or QueryInput())
        ).model_dump(mode="json")

    @tool
    async def query_diet_records(
        runtime: ToolRuntime[RunContext], query: QueryInput | None = None
    ) -> dict:
        """读取当前用户饮食记录，可按带时区的起止时间筛选。"""
        return (
            await service.query("diet", runtime.context.user_id, query or QueryInput())
        ).model_dump(mode="json")

    @tool
    async def query_exercise_records(
        runtime: ToolRuntime[RunContext], query: QueryInput | None = None
    ) -> dict:
        """读取当前用户运动记录，可按带时区的起止时间筛选。"""
        return (
            await service.query("exercise", runtime.context.user_id, query or QueryInput())
        ).model_dump(mode="json")

    @tool
    async def query_health_documents(
        runtime: ToolRuntime[RunContext], query: QueryInput | None = None
    ) -> dict:
        """读取当前用户健康文档的元数据和解析、索引状态。"""
        return (
            await service.query("document", runtime.context.user_id, query or QueryInput())
        ).model_dump(mode="json")

    @tool
    async def calculate_health_trend(
        metric_type: MetricType, runtime: ToolRuntime[RunContext], query: QueryInput | None = None
    ) -> dict:
        """从当前用户数据库计算同类指标的描述性趋势，少于两条记录时明确数据不足。"""
        return (
            await service.trend(runtime.context.user_id, metric_type, query or QueryInput())
        ).model_dump(mode="json")

    return [
        add_health_metric,
        add_diet_record,
        add_exercise_record,
        query_health_metrics,
        query_diet_records,
        query_exercise_records,
        query_health_documents,
        calculate_health_trend,
    ]
