"""The application lifespan owns provider HTTP clients; no import-time I/O."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import Settings
from app.models.demo import DemoChatModel


@asynccontextmanager
async def model_session(settings: Settings) -> AsyncIterator[BaseChatModel]:
    if settings.model_mode == "fake":
        yield DemoChatModel(cache=False)
        return

    # Settings already validated all provider fields. Explicit values avoid inheriting
    # unrelated OPENAI_* credentials/URLs. Both clients close even on startup failure.
    with httpx.Client(timeout=settings.model_timeout_seconds) as sync_client:
        async with httpx.AsyncClient(timeout=settings.model_timeout_seconds) as async_client:
            yield ChatOpenAI(
                model=settings.model_name,
                api_key=settings.model_api_key,
                base_url=str(settings.model_base_url),
                timeout=settings.model_timeout_seconds,
                max_retries=settings.model_max_retries,
                http_client=sync_client,
                http_async_client=async_client,
                use_responses_api=False,
                cache=False,
            )
