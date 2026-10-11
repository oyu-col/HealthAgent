import asyncio
import unicodedata
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.agent.runtime import extract_answer
from app.domain.schemas import iso_utc


@dataclass
class PreparedRun:
    context: RunContext
    message: str | None
    cached_answer: str | None = None


class ThreadService:
    """Single-worker admission; graph state belongs exclusively to the checkpointer."""

    def __init__(self, repository, runtime, settings):
        self.repository = repository
        self.runtime = runtime
        self.settings = settings
        self._admission = asyncio.Lock()
        self._active: set[str] = set()

    async def owned(self, user_id, thread_id):
        row = await self.repository.get(user_id, thread_id)
        if row is None:
            raise AgentError("thread_not_found", "会话不存在。", 404)
        return row

    async def metadata(self, row, snapshot=None):
        snapshot = snapshot or await self.runtime.graph.aget_state(
            {"configurable": {"thread_id": row.thread_id}}
        )
        active = (
            await self.repository.get_run(row.user_id, row.active_request_id)
            if row.active_request_id
            else None
        )
        humans = [m for m in snapshot.values.get("messages", []) if isinstance(m, HumanMessage)]
        first_message = humans[0].content if humans else active.message if active else ""
        # A plain-text preview, not model-generated HTML or a stored medical summary.
        title = " ".join(
            "".join(
                " " if character.isspace() else character
                for character in str(first_message)
                if character.isspace() or not unicodedata.category(character).startswith("C")
            ).split()
        )
        title = (title[:47] + "…") if len(title) > 48 else title or "新对话"
        running = row.thread_id in self._active
        unfinished = active is not None and active.status != "completed"
        can_resume = unfinished and not running
        # A run can need recovery even after its graph completed (e.g. interrupted
        # response persistence). The run receipt, not snapshot.next, is authoritative.
        if can_resume and humans and humans[-1].id == active.request_id and not snapshot.next:
            try:
                extract_answer(snapshot.values)
            except AgentError:
                can_resume = False
        status = (
            "running"
            if running
            else "failed"
            if unfinished and active.status == "failed"
            else "interrupted"
            if unfinished
            else "idle"
        )
        return {
            "thread_id": row.thread_id,
            "created_at": iso_utc(row.created_at),
            "active_request_id": row.active_request_id,
            "title": title,
            "status": status,
            "can_resume": can_resume,
            "pending": bool(snapshot.next),
        }

    async def create(self, user_id):
        return await self.metadata(await self.repository.create(user_id))

    async def list(self, user_id):
        return [await self.metadata(row) for row in await self.repository.list(user_id)]

    async def state(self, user_id, thread_id):
        row = await self.owned(user_id, thread_id)
        snapshot = await self.runtime.graph.aget_state({"configurable": {"thread_id": thread_id}})
        messages = []
        for message in snapshot.values.get("messages", []):
            if isinstance(message, HumanMessage):
                messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage) and not message.tool_calls:
                try:
                    messages.append(
                        {"role": "assistant", "content": extract_answer({"messages": [message]})}
                    )
                except AgentError:
                    pass
        return {**await self.metadata(row, snapshot), "messages": messages}

    @asynccontextmanager
    async def prepare(
        self, *, user_id, trace_id, message=None, thread_id=None, request_id=None, resume=False
    ):
        request_id = request_id or str(uuid4())
        async with self._admission:
            previous = await self.repository.get_run(user_id, request_id)
            if previous:
                if (thread_id and thread_id != previous.thread_id) or (
                    message is not None and message != previous.message
                ):
                    raise AgentError(
                        "request_conflict", "相同 request_id 的会话或内容发生变化。", 409
                    )
                thread_id = previous.thread_id
            elif resume:
                raise AgentError("run_not_found", "找不到可恢复的请求。", 404)
            thread = (
                await self.owned(user_id, thread_id)
                if thread_id
                else await self.repository.create(user_id)
            )
            thread_id = thread.thread_id
            if thread_id in self._active:
                raise AgentError("thread_busy", "该会话正在执行，请等待本次执行结束。", 409)
            if (
                previous
                and previous.status != "completed"
                and thread.active_request_id != request_id
            ):
                raise AgentError("stale_run", "只能恢复该会话最新的未完成请求。", 409)
            if not previous and thread.active_request_id:
                active = await self.repository.get_run(user_id, thread.active_request_id)
                if active and active.status != "completed":
                    raise AgentError("resume_required", "请先恢复该会话未完成的请求。", 409)
            if not previous:
                previous = await self.repository.create_run(user_id, thread_id, request_id, message)
            context = RunContext.create(
                self.settings, trace_id, user_id, thread_id=thread_id, operation_id=request_id
            )
            cached = previous.answer if previous.status == "completed" else None
            input_message = previous.message
            snapshot = await self.runtime.graph.aget_state(
                {"configurable": {"thread_id": thread_id}}
            )
            # A failed model/tool node resumes with None; never append the user message twice.
            latest_human = next(
                (
                    m
                    for m in reversed(snapshot.values.get("messages", []))
                    if isinstance(m, HumanMessage)
                ),
                None,
            )
            if latest_human and latest_human.id == request_id:
                if snapshot.next:
                    input_message = None
                else:
                    try:
                        cached = extract_answer(snapshot.values)
                    except AgentError:
                        raise AgentError(
                            "resume_unavailable",
                            "该请求没有可恢复的执行节点，请新建会话后重试。",
                            409,
                        ) from None
            self._active.add(thread_id)
        prepared = PreparedRun(context, input_message, cached)
        try:
            yield prepared
        finally:
            self._active.discard(thread_id)

    async def complete(self, prepared, answer):
        await self.repository.finish(
            prepared.context.user_id,
            prepared.context.operation_id,
            status="completed",
            run_id=prepared.context.run_id,
            answer=answer,
        )

    async def fail(self, prepared):
        await self.repository.finish(
            prepared.context.user_id,
            prepared.context.operation_id,
            status="failed",
            run_id=prepared.context.run_id,
        )
