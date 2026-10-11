from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.schemas import iso_utc
from app.persistence.models import (
    DietRecord,
    ExerciseRecord,
    HealthDocument,
    HealthMetric,
    WriteReceipt,
)

RECORDS = {
    "metric": HealthMetric,
    "diet": DietRecord,
    "exercise": ExerciseRecord,
    "document": HealthDocument,
}


def public_row(row) -> dict:
    return {
        column.name: iso_utc(value)
        if isinstance(value := getattr(row, column.name), datetime)
        else value
        for column in row.__table__.columns
        if column.name != "user_id"
    }


class IdempotencyConflict(Exception):
    pass


class HealthRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def add(self, kind: str, user_id: str, values: dict, key: str, payload_hash: str) -> dict:
        async def receipt(session):
            row = await session.scalar(
                select(WriteReceipt).where(
                    WriteReceipt.user_id == user_id, WriteReceipt.operation_key == key
                )
            )
            if row and row.payload_hash != payload_hash:
                raise IdempotencyConflict
            return row.result if row else None

        async with self.sessions() as session:
            existing = await receipt(session)
            if existing is not None:
                return existing
            row = RECORDS[kind](user_id=user_id, **values)
            session.add(row)
            try:
                await session.flush()
                result = public_row(row)
                session.add(
                    WriteReceipt(
                        user_id=user_id, operation_key=key, payload_hash=payload_hash, result=result
                    )
                )
                await session.commit()
                return result
            except IntegrityError:
                await session.rollback()
                existing = await receipt(session)
                if existing is None:
                    raise
                return existing

    async def query(
        self, kind: str, user_id: str, *, start=None, end=None, metric_type=None, limit=100
    ) -> list[dict]:
        model = RECORDS[kind]
        time = (
            model.measured_at
            if kind == "metric"
            else model.created_at
            if kind == "document"
            else model.timestamp
        )
        query = select(model).where(model.user_id == user_id)
        if start is not None:
            query = query.where(time >= start)
        if end is not None:
            query = query.where(time <= end)
        if kind == "metric" and metric_type:
            query = query.where(model.metric_type == metric_type)
        async with self.sessions() as session:
            rows = await session.scalars(query.order_by(time.desc(), model.id.desc()).limit(limit))
            return [public_row(row) for row in rows]
