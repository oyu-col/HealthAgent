from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError

from app.domain.schemas import iso_utc
from app.persistence.models import MemoryPreference, MemoryReceipt, now


class MemoryRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def list(self, user_id):
        async with self.sessions() as session:
            rows = await session.scalars(
                select(MemoryPreference)
                .where(MemoryPreference.user_id == user_id)
                .order_by(MemoryPreference.key)
            )
            return [
                {
                    "key": row.key,
                    "value": row.value,
                    "updated_at": iso_utc(row.updated_at),
                    "source_request_id": row.source_request_id,
                    "source_thread_id": row.source_thread_id,
                }
                for row in rows
            ]

    async def apply(self, user_id, changes, request_id, thread_id):
        async with self.sessions() as session:
            session.add(MemoryReceipt(user_id=user_id, request_id=request_id))
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                return []  # checkpoint replay must not resurrect a corrected/deleted preference
            for change in changes:
                key, value = change["key"], change["value"]
                if value is None:
                    await session.execute(
                        delete(MemoryPreference).where(
                            MemoryPreference.user_id == user_id, MemoryPreference.key == key
                        )
                    )
                else:
                    values = {
                        "user_id": user_id,
                        "key": key,
                        "value": value,
                        "updated_at": now(),
                        "source_request_id": request_id,
                        "source_thread_id": thread_id,
                    }
                    statement = insert(MemoryPreference).values(**values)
                    await session.execute(
                        statement.on_conflict_do_update(
                            index_elements=["user_id", "key"], set_=values
                        )
                    )
            await session.commit()
            return changes
