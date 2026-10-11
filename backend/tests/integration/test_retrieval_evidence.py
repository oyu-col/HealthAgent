"""Offline evidence-boundary regression tests using real ingestion and SQLite.

The provider-mode fixture below supplies synthetic vectors; it does not call an
online embedding provider or measure semantic retrieval quality.
"""

import pytest
from langchain_core.embeddings import Embeddings

from app.config import Settings
from app.persistence.database import database_session
from app.persistence.knowledge_repository import KnowledgeRepository
from app.rag.embeddings import LocalHashEmbeddings
from app.services.knowledge import KnowledgeService


@pytest.fixture
async def knowledge(settings):
    async with database_session(settings.data_dir) as sessions:
        yield KnowledgeService(
            KnowledgeRepository(sessions),
            LocalHashEmbeddings(settings.embedding_dimensions),
            settings,
        )


async def test_local_hash_collision_is_not_evidence(knowledge):
    # Different single tokens collide in the existing 1024-dimensional index.
    # Raising the cosine threshold cannot reject this false match: score is 1.
    assert knowledge.embedding.embed_query("synthetic3") == knowledge.embedding.embed_query(
        "synthetic68"
    )
    document = await knowledge.ingest("alice", "collision.txt", b"synthetic3")
    assert document["index_status"] == "indexed"

    result = await knowledge.search("alice", "synthetic68")

    assert result.success
    assert result.data["citations"] == []


@pytest.mark.parametrize(
    ("text", "query"),
    [
        ("synthetic3", "ＳＹＮＴＨＥＴＩＣ３"),
        ("daily walking diary", "walking"),
        ("合成睡眠计划：晚上九点关闭屏幕。", "睡眠计划"),
    ],
    ids=["normalized-same-token", "shared-english-token", "chinese-overlap"],
)
async def test_local_hash_keeps_actual_lexical_evidence(knowledge, text, query):
    document = await knowledge.ingest("alice", "matching.txt", text.encode("utf-8"))
    assert document["index_status"] == "indexed"

    result = await knowledge.search("alice", query)

    assert result.success
    assert len(result.data["citations"]) == 1
    citation = result.data["citations"][0]
    assert citation["document_id"] == document["id"]
    assert citation["text"] == text
    assert citation["citation_id"].startswith("C-")
    assert citation["page"] == 1


class SyntheticSemanticEmbeddings(Embeddings):
    """A controlled vector fixture, not an online provider or a quality model."""

    def __init__(self, dimensions):
        self.dimensions = dimensions

    def embed_query(self, text):
        return [1.0] + [0.0] * (self.dimensions - 1)

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


async def test_provider_vectors_can_match_without_lexical_overlap(tmp_path):
    settings = Settings(
        model_mode="fake",
        data_dir=tmp_path,
        embedding_mode="provider",
        embedding_model="synthetic-semantic-test-fixture",
        model_base_url="https://provider.invalid/v1",
        model_api_key="synthetic-test-value-not-a-real-credential",
        _env_file=None,
    )
    async with database_session(tmp_path) as sessions:
        knowledge = KnowledgeService(
            KnowledgeRepository(sessions),
            SyntheticSemanticEmbeddings(settings.embedding_dimensions),
            settings,
        )
        document = await knowledge.ingest("alice", "semantic.txt", "入夜后安静休息。".encode())
        assert document["index_status"] == "indexed"

        result = await knowledge.search("alice", "nighttime rest")

        assert result.success
        assert [item["document_id"] for item in result.data["citations"]] == [document["id"]]
        assert result.data["embedding_mode"] == "provider"


async def test_lexical_evidence_keeps_owner_and_scope_filters(knowledge):
    alice = await knowledge.ingest("alice", "alice.txt", b"walking diary alice")
    bob = await knowledge.ingest("bob", "bob.txt", b"walking diary bob")
    public = await knowledge.ingest(
        "system-public", "public.txt", b"walking diary public", visibility="public"
    )
    expected = {
        "personal": {alice["id"]},
        "public": {public["id"]},
        "both": {alice["id"], public["id"]},
    }

    for scope, document_ids in expected.items():
        result = await knowledge.search("alice", "walking diary", scope=scope)
        assert result.success
        actual = {item["document_id"] for item in result.data["citations"]}
        assert actual == document_ids
        assert bob["id"] not in actual
