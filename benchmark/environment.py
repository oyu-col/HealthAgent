"""Temporary fixture preparation and scoped, counted fault injection."""

import asyncio
from contextlib import contextmanager
from uuid import uuid4

from benchmark.observation import OWNER


async def seed(app, case):
    environment = case.get("initial_environment", {})
    for row in environment.get("records", []):
        result = await app.state.health.add(
            row["kind"], row.get("user_id", OWNER), row["record"], str(uuid4())
        )
        if not result.success:
            raise ValueError("invalid benchmark record fixture")
    documents = {}
    for document in environment.get("documents", []):
        result = await app.state.knowledge.ingest(
            document.get("user_id", OWNER),
            document["filename"],
            document["text"].encode(),
            visibility=document.get("visibility", "personal"),
            source=document.get("source", "synthetic-benchmark"),
        )
        if result["index_status"] != "indexed":
            raise ValueError("benchmark document fixture failed to index")
        documents[document["key"]] = result["id"]
    for key, value in environment.get("preferences", {}).items():
        await app.state.memory.update(OWNER, key, value)
    return documents


@contextmanager
def inject_fault(app, fault, settings):
    counter = {"triggered": 0, "attempts": 0}
    if not fault:
        yield counter
        return
    target = fault["target"]
    instance = {
        "query": app.state.health,
        "add": app.state.health,
        "search": app.state.knowledge,
        "trace_finish": app.state.traces,
    }[target]
    method = "finish" if target == "trace_finish" else target
    original = getattr(instance, method)

    async def wrapped(*args, **kwargs):
        if fault.get("record_kind") and args[0] != fault["record_kind"]:
            return await original(*args, **kwargs)
        counter["attempts"] += 1
        kind = fault["kind"]
        if counter["triggered"] and kind != "permanent":
            return await original(*args, **kwargs)
        counter["triggered"] += 1
        if kind == "transient_once":
            raise ConnectionError("Synthetic transient failure")
        if kind in {"permanent", "finish_once"}:
            raise RuntimeError("Synthetic benchmark failure")
        if kind == "timeout_once":
            # The write may have committed even though the caller observes a timeout.
            if target == "add":
                await original(*args, **kwargs)
            await asyncio.sleep(settings.tool_timeout_seconds + 0.2)
        return await original(*args, **kwargs)

    setattr(instance, method, wrapped)
    try:
        yield counter
    finally:
        setattr(instance, method, original)
