from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    age: Mapped[int | None]
    height: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class OwnedRecord:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)


class HealthMetric(OwnedRecord, Base):
    __tablename__ = "health_metrics"
    metric_type: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    measured_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class DietRecord(OwnedRecord, Base):
    __tablename__ = "diet_records"
    food_name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[str] = mapped_column(String(200))
    meal_type: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    nutrition_info: Mapped[dict | None] = mapped_column(JSON)


class ExerciseRecord(OwnedRecord, Base):
    __tablename__ = "exercise_records"
    exercise_type: Mapped[str] = mapped_column(String(200))
    duration: Mapped[float]
    distance: Mapped[float | None]
    calories: Mapped[float | None]
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)


class HealthDocument(OwnedRecord, Base):
    __tablename__ = "health_documents"
    filename: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    index_status: Mapped[str] = mapped_column(String(20), default="pending")


class WriteReceipt(Base):
    __tablename__ = "write_receipts"
    __table_args__ = (UniqueConstraint("user_id", "operation_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64))
    operation_key: Mapped[str] = mapped_column(String(128))
    payload_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)


class ThreadRecord(Base):
    __tablename__ = "threads"
    thread_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    active_request_id: Mapped[str | None] = mapped_column(String(36))


class ChatRun(Base):
    __tablename__ = "chat_runs"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(36), index=True)
    message: Mapped[str]
    status: Mapped[str] = mapped_column(String(16), default="pending")
    answer: Mapped[str | None]
    run_id: Mapped[str | None] = mapped_column(String(36))


class DocumentIndex(Base):
    __tablename__ = "document_indexes"
    __table_args__ = (UniqueConstraint("user_id", "visibility", "content_hash", "index_version"),)
    document_id: Mapped[str] = mapped_column(ForeignKey("health_documents.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    visibility: Mapped[str] = mapped_column(String(16))
    content_hash: Mapped[str] = mapped_column(String(64))
    index_version: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(1000))
    error_code: Mapped[str | None] = mapped_column(String(32))


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("document_indexes.document_id"), index=True)
    text: Mapped[str]
    page: Mapped[int]
    start_index: Mapped[int]
    embedding: Mapped[list] = mapped_column(JSON)


class MemoryPreference(Base):
    __tablename__ = "memory_preferences"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    source_request_id: Mapped[str] = mapped_column(String(36))
    source_thread_id: Mapped[str | None] = mapped_column(String(36))


class MemoryReceipt(Base):
    __tablename__ = "memory_receipts"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
