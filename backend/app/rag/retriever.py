import asyncio
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.rag.embeddings import lexical_features, normalize_vector


class ScopedVectorRetriever(BaseRetriever):
    repository: Any
    embedding: Any
    user_id: str
    version: str
    dimensions: int
    scope: str = "both"
    k: int = 5
    require_lexical_overlap: bool = False

    def _get_relevant_documents(self, query, *, run_manager):
        raise NotImplementedError("Use the async retriever")

    async def _aget_relevant_documents(self, query, *, run_manager):
        rows = await self.repository.candidates(self.user_id, self.version, self.scope)
        if len(rows) > 5000:
            raise ValueError("scoped index exceeds the local retrieval capacity")
        vector = normalize_vector(await self.embedding.aembed_query(query), self.dimensions)
        query_features = set(lexical_features(query)) if self.require_lexical_overlap else set()

        def rank():
            ranked = []
            for chunk, index, document in rows:
                # Defense in depth after SQL filtering, before returning source text.
                if index.visibility != "public" and index.user_id != self.user_id:
                    continue
                # A hash-bucket collision is not lexical evidence. Semantic provider
                # vectors can legitimately match without any shared surface features.
                if self.require_lexical_overlap and query_features.isdisjoint(
                    lexical_features(chunk.text)
                ):
                    continue
                candidate = normalize_vector(chunk.embedding, self.dimensions)
                score = sum(a * b for a, b in zip(vector, candidate, strict=True))
                if score >= 0.08:
                    ranked.append((score, chunk, index, document))
            ranked.sort(key=lambda item: (-item[0], item[1].id))
            return [
                Document(
                    page_content=chunk.text,
                    metadata={
                        "citation_id": "C-" + chunk.id,
                        "document_id": document.id,
                        "filename": document.filename,
                        "page": chunk.page,
                        "start_index": chunk.start_index,
                        "source": index.source,
                        "visibility": index.visibility,
                        "index_version": index.index_version,
                        "score": round(score, 6),
                    },
                )
                for score, chunk, index, document in ranked[: self.k]
            ]

        return await asyncio.to_thread(rank)
