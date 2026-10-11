"""Bounded, owner-scoped execution metadata, separate from health fact models."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, delete, func, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.agent.errors import AgentError


class TraceBase(DeclarativeBase):
    pass


class TraceRecord(TraceBase):
    __tablename__ = "execution_traces"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    thread_id: Mapped[str | None] = mapped_column(String(36), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    summary: Mapped[dict] = mapped_column(JSON)
    events: Mapped[list] = mapped_column(JSON)


class TraceRepository:
    def __init__(self, sessions, *, max_total=1000, max_per_user=250):
        self.sessions = sessions
        self.max_total = max_total
        self.max_per_user = max_per_user
        self._admission = asyncio.Lock()

    async def initialize(self):
        async with self.sessions() as session:
            connection = await session.connection()
            await connection.run_sync(TraceBase.metadata.create_all)
            # Single-worker deployment: surviving running rows belong to an earlier process.
            rows = await session.scalars(select(TraceRecord).where(TraceRecord.status == "running"))
            for row in rows:
                row.status = "interrupted"
                row.summary = {
                    **row.summary,
                    "status": "interrupted",
                    "termination_reason": "process_interrupted",
                    "finished_at": None,
                    "latency_ms": None,
                    "capture_complete": False,
                    **{
                        name: None
                        for name in (
                            "model_calls",
                            "tool_calls",
                            "subagent_calls",
                            "model_retries",
                            "tool_retries",
                            "retry_count",
                            "total_steps",
                        )
                    },
                    "token_usage": {
                        "input_tokens": None,
                        "output_tokens": None,
                        "total_tokens": None,
                        "complete": False,
                    },
                }
            await session.commit()

    async def _prune(self, session, user_id):
        owner_count = await session.scalar(
            select(func.count()).select_from(TraceRecord).where(TraceRecord.user_id == user_id)
        )
        if owner_count >= self.max_per_user:
            user_overflow = (
                select(TraceRecord.run_id)
                .where(TraceRecord.user_id == user_id, TraceRecord.status != "running")
                .order_by(TraceRecord.started_at, TraceRecord.run_id)
                .limit(owner_count - self.max_per_user + 1)
            )
            await session.execute(delete(TraceRecord).where(TraceRecord.run_id.in_(user_overflow)))
        total_count = await session.scalar(select(func.count()).select_from(TraceRecord))
        if total_count >= self.max_total:
            total_overflow = (
                select(TraceRecord.run_id)
                .where(TraceRecord.status != "running")
                .order_by(TraceRecord.started_at, TraceRecord.run_id)
                .limit(total_count - self.max_total + 1)
            )
            await session.execute(delete(TraceRecord).where(TraceRecord.run_id.in_(total_overflow)))

    async def start(self, user_id, summary):
        # SQLite's deferred transactions do not serialize the count/insert pair.
        # The supported single worker needs one lock through commit to reserve
        # capacity across requests for different threads and users.
        async with self._admission, self.sessions() as session, session.begin():
            await self._prune(session, user_id)
            # Do not evict a running trace. Enforce capacity before accepting more work.
            count = await session.scalar(select(func.count()).select_from(TraceRecord))
            owner_count = await session.scalar(
                select(func.count()).select_from(TraceRecord).where(TraceRecord.user_id == user_id)
            )
            if count >= self.max_total or owner_count >= self.max_per_user:
                raise AgentError("trace_capacity", "执行记录容量暂满，请稍后重试。", 503)
            session.add(
                TraceRecord(
                    run_id=summary["run_id"],
                    trace_id=summary["trace_id"],
                    user_id=user_id,
                    thread_id=summary["thread_id"],
                    started_at=datetime.fromisoformat(summary["started_at"])
                    .astimezone(UTC)
                    .replace(tzinfo=None),
                    status="running",
                    summary=summary,
                    events=[],
                )
            )

    async def finish(self, user_id, summary, events):
        async with self.sessions() as session, session.begin():
            result = await session.execute(
                update(TraceRecord)
                .where(TraceRecord.user_id == user_id, TraceRecord.run_id == summary["run_id"])
                .values(status=summary["status"], summary=summary, events=events)
            )
            if result.rowcount != 1:
                raise AgentError("trace_unavailable", "执行记录无法保存，请恢复会话后重试。", 503)

    async def list(self, user_id, *, thread_id=None, limit=20, offset=0):
        statement = select(TraceRecord).where(TraceRecord.user_id == user_id)
        if thread_id:
            statement = statement.where(TraceRecord.thread_id == thread_id)
        statement = (
            statement.order_by(TraceRecord.started_at.desc(), TraceRecord.run_id.desc())
            .limit(limit)
            .offset(offset)
        )
        async with self.sessions() as session:
            return [row.summary for row in await session.scalars(statement)]

    async def get(self, user_id, trace_id):
        async with self.sessions() as session:
            row = await session.scalar(
                select(TraceRecord)
                .where(TraceRecord.user_id == user_id, TraceRecord.trace_id == trace_id)
                .order_by(TraceRecord.started_at.desc())
            )
            if row is None:
                raise AgentError("trace_not_found", "执行记录不存在。", 404)
            return {**row.summary, "events": row.events}
