from sqlalchemy import delete, or_, select

from app.persistence.health_repository import public_row
from app.persistence.models import DocumentIndex, HealthDocument, KnowledgeChunk


class KnowledgeRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    def metadata(document, index):
        return {
            **public_row(document),
            "visibility": index.visibility,
            "source": index.source,
            "index_version": index.index_version,
            "error_code": index.error_code,
        }

    async def begin(self, user_id, filename, visibility, content_hash, index_version, source):
        async with self.sessions() as session:
            existing = await session.scalar(
                select(DocumentIndex).where(
                    DocumentIndex.user_id == user_id,
                    DocumentIndex.visibility == visibility,
                    DocumentIndex.content_hash == content_hash,
                    DocumentIndex.index_version == index_version,
                )
            )
            if existing:
                document = await session.get(HealthDocument, existing.document_id)
                return self.metadata(document, existing)
            document = HealthDocument(
                user_id=user_id,
                filename=filename,
                document_type=filename.rsplit(".", 1)[-1].lower(),
            )
            session.add(document)
            await session.flush()
            index = DocumentIndex(
                document_id=document.id,
                user_id=user_id,
                visibility=visibility,
                content_hash=content_hash,
                index_version=index_version,
                source=source,
            )
            session.add(index)
            await session.commit()
            return self.metadata(document, index)

    async def finish(
        self,
        user_id,
        document_id,
        *,
        chunks=None,
        parse_status="parsed",
        index_status="indexed",
        error_code=None,
    ):
        async with self.sessions() as session:
            document = await session.scalar(
                select(HealthDocument).where(
                    HealthDocument.id == document_id, HealthDocument.user_id == user_id
                )
            )
            index = await session.get(DocumentIndex, document_id)
            document.parse_status, document.index_status, index.error_code = (
                parse_status,
                index_status,
                error_code,
            )
            await session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
            )
            if chunks:
                session.add_all(
                    KnowledgeChunk(document_id=document_id, **chunk) for chunk in chunks
                )
            await session.commit()
            return self.metadata(document, index)

    async def candidates(self, user_id, version, scope):
        # Apply authorization in SQL before scoring or top-k; exclude other users' private chunks.
        condition = DocumentIndex.visibility == "public"
        personal = (DocumentIndex.visibility == "personal") & (DocumentIndex.user_id == user_id)
        if scope == "personal":
            condition = personal
        elif scope == "both":
            condition = or_(condition, personal)
        query = (
            select(KnowledgeChunk, DocumentIndex, HealthDocument)
            .join(DocumentIndex, KnowledgeChunk.document_id == DocumentIndex.document_id)
            .join(HealthDocument, HealthDocument.id == DocumentIndex.document_id)
            .where(
                condition,
                DocumentIndex.index_version == version,
                HealthDocument.index_status == "indexed",
            )
            .limit(5001)
        )
        async with self.sessions() as session:
            return list((await session.execute(query)).all())

    async def list(self, user_id):
        async with self.sessions() as session:
            rows = await session.execute(
                select(HealthDocument, DocumentIndex)
                .join(DocumentIndex)
                .where(HealthDocument.user_id == user_id)
                .order_by(HealthDocument.created_at.desc())
                .limit(100)
            )
            return [self.metadata(doc, index) for doc, index in rows]
