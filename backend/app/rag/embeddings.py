import hashlib
import math
import re
import unicodedata
from contextlib import asynccontextmanager

import httpx
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


def lexical_features(text):
    """Return unhashed features shared by local indexing and evidence filtering."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    terms = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", normalized)
    return terms + ["".join(terms[i : i + 2]) for i in range(len(terms) - 1)]


class LocalHashEmbeddings(Embeddings):
    """Deterministic lexical n-gram vectors; NOT neural semantic embeddings."""

    def __init__(self, dimensions=1024):
        self.dimensions = dimensions

    def embed_query(self, text):
        vector = [0.0] * self.dimensions
        for token in lexical_features(text):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1
        return [x / norm for x in vector]

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


def normalize_vector(vector, dimensions):
    if len(vector) != dimensions or not all(
        isinstance(x, (float, int)) and math.isfinite(x) for x in vector
    ):
        raise ValueError("invalid embedding dimensions or values")
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return [0.0] * dimensions
    return [x / norm for x in vector]


@asynccontextmanager
async def embedding_session(settings):
    if settings.embedding_mode == "local_hash":
        yield LocalHashEmbeddings(settings.embedding_dimensions)
        return
    with httpx.Client(timeout=settings.model_timeout_seconds) as sync_client:
        async with httpx.AsyncClient(timeout=settings.model_timeout_seconds) as async_client:
            yield OpenAIEmbeddings(
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                api_key=settings.model_api_key,
                base_url=str(settings.model_base_url),
                http_client=sync_client,
                http_async_client=async_client,
                max_retries=settings.model_max_retries,
                request_timeout=settings.model_timeout_seconds,
                check_embedding_ctx_length=False,
                chunk_size=32,
            )


def index_version(settings):
    model = (
        "lexical-ngram-v1" if settings.embedding_mode == "local_hash" else settings.embedding_model
    )
    return (
        f"{settings.embedding_mode}:{model}:{settings.embedding_dimensions}:chunk600-overlap80-v1"
    )
