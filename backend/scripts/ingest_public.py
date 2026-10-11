"""Operator-only local command; the HTTP API never grants public-write access."""

import argparse
import asyncio
import json
from pathlib import Path

from app.config import load_settings
from app.persistence.database import database_session
from app.persistence.knowledge_repository import KnowledgeRepository
from app.rag.embeddings import embedding_session
from app.services.knowledge import KnowledgeService


async def ingest(args):
    settings = load_settings()
    path = Path(args.path)
    content = await asyncio.to_thread(path.read_bytes)
    async with (
        database_session(settings.data_dir) as sessions,
        embedding_session(settings) as embedding,
    ):
        service = KnowledgeService(KnowledgeRepository(sessions), embedding, settings)
        result = await service.ingest(
            "system-public", path.name, content, visibility="public", source=args.source
        )
        print(json.dumps(result, ensure_ascii=False))
        if result["index_status"] != "indexed":
            raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Import an operator-reviewed public knowledge file"
    )
    parser.add_argument("path")
    parser.add_argument(
        "--source",
        required=True,
        help="Original source URL or publication identifier; never fabricated",
    )
    asyncio.run(ingest(parser.parse_args()))


if __name__ == "__main__":
    main()
