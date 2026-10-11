"""App factory: uvicorn app.main:create_app --factory --host 127.0.0.1."""

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from starlette.exceptions import HTTPException

from app.agent.errors import AgentError
from app.agent.runtime import HealthAgentRuntime
from app.agents.lead_agent import build_lead_agent
from app.api.chat import router
from app.api.documents import router as documents_router
from app.api.memory import router as memory_router
from app.api.records import router as records_router
from app.api.schemas import ErrorDetail, ErrorResponse
from app.api.session import router as session_router
from app.api.stream import router as stream_router
from app.api.threads import router as threads_router
from app.api.traces import router as traces_router
from app.config import PROJECT_ROOT, Settings, load_settings
from app.memory.middleware import PreferenceMemoryMiddleware
from app.models.factory import model_session
from app.persistence.database import database_session
from app.persistence.health_repository import HealthRepository
from app.persistence.knowledge_repository import KnowledgeRepository
from app.persistence.memory_repository import MemoryRepository
from app.persistence.thread_repository import ThreadRepository
from app.persistence.trace_repository import TraceRepository
from app.rag.embeddings import embedding_session
from app.services.health import HealthService
from app.services.knowledge import KnowledgeService
from app.services.memory import MemoryService
from app.services.threads import ThreadService
from app.tools.health import health_tools
from app.tools.knowledge import knowledge_tool

logger = logging.getLogger("health_agent.api")


def error_response(request: Request, code: str, message: str, status: int) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            trace_id=request.state.trace_id,
            thread_id=getattr(request.state, "thread_id", None),
            request_id=getattr(request.state, "request_id", None),
        )
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def create_app(
    *,
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
    frontend_dist: Path | None = None,
) -> FastAPI:
    """A supplied model belongs to the caller; lifespan owns factory-created clients."""
    resolved_settings = settings if settings is not None else load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            sessions = await stack.enter_async_context(database_session(resolved_settings.data_dir))
            app.state.sessions = sessions
            app.state.traces = TraceRepository(sessions)
            await app.state.traces.initialize()
            app.state.health = HealthService(HealthRepository(sessions))
            app.state.memory = MemoryService(MemoryRepository(sessions))
            embedding = await stack.enter_async_context(embedding_session(resolved_settings))
            app.state.knowledge = KnowledgeService(
                KnowledgeRepository(sessions), embedding, resolved_settings
            )
            checkpointer = await stack.enter_async_context(
                AsyncSqliteSaver.from_conn_string(
                    str(resolved_settings.data_dir / "checkpoints.db")
                )
            )
            await checkpointer.setup()
            active_model = model
            if active_model is None:
                active_model = await stack.enter_async_context(model_session(resolved_settings))
            app.state.runtime = HealthAgentRuntime(
                build_lead_agent(
                    active_model,
                    tools=health_tools(app.state.health) + [knowledge_tool(app.state.knowledge)],
                    checkpointer=checkpointer,
                    middleware=[
                        PreferenceMemoryMiddleware(
                            app.state.memory, enabled=resolved_settings.memory_enabled
                        )
                    ],
                    max_tool_calls=resolved_settings.max_tool_calls,
                    settings=resolved_settings,
                ),
                resolved_settings,
                app.state.traces,
            )
            app.state.threads = ThreadService(
                ThreadRepository(sessions), app.state.runtime, resolved_settings
            )
            try:
                yield
            finally:
                app.state.runtime = None

    app = FastAPI(title="HealthAgent", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings

    @app.middleware("http")
    async def request_identity(request: Request, call_next):
        # Never trust a client-provided identity or trace id.
        request.state.trace_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            # A raw exception can contain health text or provider credentials.
            logger.error("request_failed trace_id=%s", request.state.trace_id)
            response = error_response(request, "internal_error", "请求处理失败。", 500)
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AgentError)
    async def agent_error_handler(request: Request, error: AgentError):
        return error_response(request, error.code, error.message, error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, error: RequestValidationError):
        # FastAPI's default errors include the user's raw input. Do not return it.
        return error_response(request, "invalid_request", "请求格式或 message 字段不合法。", 422)

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, error: HTTPException):
        return error_response(request, "http_error", "请求的路径或方法不可用。", error.status_code)

    app.include_router(router)
    app.include_router(threads_router)
    app.include_router(stream_router)
    app.include_router(documents_router)
    app.include_router(memory_router)
    app.include_router(records_router)
    app.include_router(session_router)
    app.include_router(traces_router)

    # Hash-based UI navigation needs only / and /assets. Never use a catch-all
    # fallback: unknown API paths must retain their JSON 404 responses.
    dist = frontend_dist if frontend_dist is not None else PROJECT_ROOT / "frontend" / "dist"
    if (dist / "index.html").is_file():

        @app.get("/", include_in_schema=False)
        async def frontend_index():
            return FileResponse(dist / "index.html", media_type="text/html")

        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="frontend-assets")
    return app
