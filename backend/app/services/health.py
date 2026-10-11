import hashlib
import json
from datetime import UTC, datetime
from statistics import mean

from app.domain.schemas import DietInput, ExerciseInput, MetricInput, QueryInput, ToolResult
from app.persistence.health_repository import HealthRepository, IdempotencyConflict

INPUTS = {"metric": MetricInput, "diet": DietInput, "exercise": ExerciseInput}


def utc_naive(value: datetime | None):
    return value.astimezone(UTC).replace(tzinfo=None) if value else None


class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository

    async def add(self, kind, user_id, record, operation_key):
        validated = INPUTS[kind].model_validate(record)
        # Hash the input BEFORE applying a default time so retries remain identical.
        payload = kind + json.dumps(
            validated.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
        )
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        values = validated.model_dump()
        field = "measured_at" if kind == "metric" else "timestamp"
        values[field] = utc_naive(values[field] or datetime.now(UTC))
        try:
            return ToolResult.ok(
                await self.repository.add(kind, user_id, values, operation_key, payload_hash)
            )
        except IdempotencyConflict:
            return ToolResult.fail(
                "idempotency_conflict", "相同操作标识的参数发生变化，请核对已有记录。"
            )

    async def query(self, kind, user_id, query: QueryInput):
        rows = await self.repository.query(
            kind,
            user_id,
            start=utc_naive(query.start),
            end=utc_naive(query.end),
            metric_type=query.metric_type,
            limit=query.limit + 1,
        )
        return ToolResult.ok({"records": rows[: query.limit], "truncated": len(rows) > query.limit})

    async def trend(self, user_id, metric_type, query: QueryInput):
        rows = await self.repository.query(
            "metric",
            user_id,
            start=utc_naive(query.start),
            end=utc_naive(query.end),
            metric_type=metric_type,
            limit=10001,
        )
        if len(rows) > 10000:
            return ToolResult.fail("range_too_large", "数据过多，请缩小时间范围后重新计算。")
        if len(rows) < 2:
            return ToolResult.fail("insufficient_data", "至少需要两条同类指标记录。")
        values = [r["value"] for r in rows]
        return ToolResult.ok(
            {
                "metric_type": metric_type,
                "unit": rows[0]["unit"],
                "count": len(rows),
                "mean": mean(values),
                "min": min(values),
                "max": max(values),
                "first": rows[-1],
                "last": rows[0],
                "change": values[0] - values[-1],
                "interpretation": "描述性统计，不构成医学诊断。",
            }
        )
