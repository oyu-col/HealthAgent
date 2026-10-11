from sqlalchemy import select, update

from app.persistence.models import ChatRun, ThreadRecord


class ThreadRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def create(self, user_id):
        async with self.sessions() as session:
            row = ThreadRecord(user_id=user_id)
            session.add(row)
            await session.commit()
            return row

    async def get(self, user_id, thread_id):
        async with self.sessions() as session:
            return await session.scalar(
                select(ThreadRecord).where(
                    ThreadRecord.user_id == user_id, ThreadRecord.thread_id == thread_id
                )
            )

    async def list(self, user_id):
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(ThreadRecord)
                    .where(ThreadRecord.user_id == user_id)
                    .order_by(ThreadRecord.created_at.desc())
                    .limit(100)
                )
            )

    async def get_run(self, user_id, request_id):
        async with self.sessions() as session:
            return await session.get(ChatRun, (user_id, request_id))

    async def create_run(self, user_id, thread_id, request_id, message):
        async with self.sessions() as session:
            row = ChatRun(
                user_id=user_id, thread_id=thread_id, request_id=request_id, message=message
            )
            session.add(row)
            thread = await session.scalar(
                select(ThreadRecord).where(
                    ThreadRecord.thread_id == thread_id, ThreadRecord.user_id == user_id
                )
            )
            thread.active_request_id = request_id
            await session.commit()
            return row

    async def finish(self, user_id, request_id, *, status, run_id, answer=None):
        async with self.sessions() as session:
            # A completed receipt is immutable. Replaying it creates a new trace,
            # whose failure must never erase the original idempotent answer.
            await session.execute(
                update(ChatRun)
                .where(
                    ChatRun.user_id == user_id,
                    ChatRun.request_id == request_id,
                    ChatRun.status != "completed",
                )
                .values(status=status, run_id=run_id, answer=answer)
            )
            await session.commit()
