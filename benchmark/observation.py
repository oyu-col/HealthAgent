"""In-memory observation of synthetic runs. Raw payloads never enter report files."""

import json

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import ToolMessage
from sqlalchemy import select

from app.domain.schemas import iso_utc
from app.persistence.models import (
    DietRecord,
    DocumentIndex,
    ExerciseRecord,
    HealthDocument,
    HealthMetric,
    KnowledgeChunk,
    MemoryPreference,
)

OWNER = "benchmark-user"
TABLES = {"metric": HealthMetric, "diet": DietRecord, "exercise": ExerciseRecord}


class Capture(AsyncCallbackHandler):
    run_inline = True
    raise_error = True

    def __init__(self):
        self.roles = {}
        self.tools = {}
        self.proposals = []
        self.observations = []
        self.model_errors = []

    async def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self.roles[str(run_id)] = (metadata or {}).get("health_agent_name", "health_lead_agent")

    async def on_llm_end(self, response, *, run_id, **kwargs):
        for generation in response.generations:
            for item in generation:
                message = getattr(item, "message", None)
                for call in getattr(message, "tool_calls", []):
                    self.proposals.append(
                        {
                            "name": call["name"],
                            "args": call["args"],
                            "agent_name": self.roles.get(str(run_id), "health_lead_agent"),
                        }
                    )

    async def on_llm_error(self, error, **kwargs):
        # Types and integer status codes only; never exception messages or provider URLs.
        chain, current = [], error
        for _ in range(5):
            if current is None:
                break
            entry = {"type": type(current).__name__}
            for attribute in ("errno", "status_code"):
                value = getattr(current, attribute, None)
                if type(value) is int:
                    entry[attribute] = value
            chain.append(entry)
            current = current.__cause__
        self.model_errors.append(chain)

    async def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, **kwargs):
        self.tools[str(run_id)] = {
            "name": (serialized or {}).get("name", "unknown"),
            "agent_name": (metadata or {}).get("health_agent_name", "health_lead_agent"),
        }

    async def on_tool_end(self, output, *, run_id, **kwargs):
        self.add(self.tools.get(str(run_id), {}), output)

    def add(self, identity, output):
        if isinstance(output, ToolMessage):
            identity = {"name": output.name, **identity}
            output = output.content
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (TypeError, ValueError):
                return
        if isinstance(output, dict) and isinstance(output.get("success"), bool):
            entry = {"agent_name": "health_lead_agent", **identity, "result": output}
            if entry not in self.observations:
                self.observations.append(entry)


async def snapshot(sessions):
    from datetime import datetime

    result = {}
    async with sessions() as session:
        for kind, table in TABLES.items():
            result[kind] = [
                {
                    column.name: iso_utc(value)
                    if isinstance(value := getattr(row, column.name), datetime)
                    else value
                    for column in table.__table__.columns
                }
                for row in await session.scalars(select(table).order_by(table.id))
            ]
        preferences = {
            row.key: row.value
            for row in await session.scalars(
                select(MemoryPreference).where(MemoryPreference.user_id == OWNER)
            )
        }
    return result, preferences


def evidence(observations):
    found = {}

    def visit(value):
        if isinstance(value, dict):
            if all(key in value for key in ("citation_id", "document_id", "text")):
                found[value["citation_id"]] = value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for observation in observations:
        visit(observation["result"])
    return list(found.values())


async def verified_evidence(sessions, observations):
    """Check citations against actual indexed chunks, not just the tool's claims."""
    verified = []
    async with sessions() as session:
        for citation in evidence(observations):
            key = citation["citation_id"]
            if not isinstance(key, str) or not key.startswith("C-"):
                continue
            row = (
                await session.execute(
                    select(KnowledgeChunk, DocumentIndex, HealthDocument)
                    .join(DocumentIndex, KnowledgeChunk.document_id == DocumentIndex.document_id)
                    .join(HealthDocument, HealthDocument.id == DocumentIndex.document_id)
                    .where(KnowledgeChunk.id == key[2:])
                )
            ).first()
            if row is None:
                continue
            chunk, index, document = row
            if index.visibility != "public" and index.user_id != OWNER:
                continue
            if document.index_status != "indexed":
                continue
            if citation["document_id"] != document.id or citation["text"] != chunk.text:
                continue
            if (
                citation.get("page") != chunk.page
                or citation.get("index_version") != index.index_version
            ):
                continue
            verified.append(citation)
    return verified
