import io
import json

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import create_app
from tests.fakes import ToolChatModel


async def test_text_pdf_upload_and_scanned_pdf_failure(settings):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 250 Td (Synthetic walking diary) Tj ET")
    page[NameObject("/Contents")] = stream
    buffer = io.BytesIO()
    writer.write(buffer)
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("synthetic.pdf", buffer.getvalue(), "application/pdf")},
            )
            assert response.json()["index_status"] == "indexed"
            citations = (await app.state.knowledge.search("local-user", "walking diary")).data[
                "citations"
            ]
            assert citations[0]["page"] == 1 and "Synthetic walking" in citations[0]["text"]
        empty = PdfWriter()
        empty.add_blank_page(width=300, height=300)
        blank = io.BytesIO()
        empty.write(blank)
        failed = await app.state.knowledge.ingest("local-user", "scan.pdf", blank.getvalue())
        assert failed["parse_status"] == "failed"


async def test_embedding_failure_is_atomic_and_retryable_by_upload(settings):
    app = create_app(settings=settings)

    class BrokenEmbedding:
        async def aembed_documents(self, texts):
            raise RuntimeError("SECRET")

    async with app.router.lifespan_context(app):
        embedding = app.state.knowledge.embedding
        app.state.knowledge.embedding = BrokenEmbedding()
        failed = await app.state.knowledge.ingest(
            "local-user", "retry.txt", "合成步行计划".encode()
        )
        assert failed["parse_status"] == "parsed" and failed["index_status"] == "failed"
        assert "SECRET" not in json.dumps(failed)
        app.state.knowledge.embedding = embedding
        assert not (await app.state.knowledge.search("local-user", "合成步行计划")).data[
            "citations"
        ]
        success = await app.state.knowledge.ingest(
            "local-user", "retry.txt", "合成步行计划".encode()
        )
        assert success["id"] == failed["id"] and success["index_status"] == "indexed"


async def test_ingest_deduplicate_retrieve_cite_and_persist(settings):
    app = create_app(
        settings=settings,
        model=ToolChatModel(
            tool_name="search_health_knowledge", arguments={"query": "合成睡眠计划"}
        ),
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = {
                "filename": "合成指南.md",
                "text": "# 合成睡眠计划\n本文件仅是测试样本，记录作息与感受，不提供医学建议。",
            }
            created = (await client.post("/api/documents/text", json=payload)).json()
            repeated = (await client.post("/api/documents/text", json=payload)).json()
            assert created["id"] == repeated["id"]
            assert created["parse_status"] == "parsed" and created["index_status"] == "indexed"
            result = json.loads(
                (await client.post("/api/chat", json={"message": "查合成睡眠计划"})).json()[
                    "answer"
                ]
            )
            assert result["success"] and result["data"]["citations"]
            evidence = result["data"]["citations"][0]
            assert evidence["document_id"] == created["id"]
            assert (
                evidence["citation_id"]
                and evidence["index_version"]
                and evidence["filename"] == payload["filename"]
            )
    restarted = create_app(settings=settings)
    async with restarted.router.lifespan_context(restarted):
        result = await restarted.state.knowledge.search("local-user", "合成睡眠计划")
        assert result.data["citations"][0]["document_id"] == created["id"]


async def test_public_personal_isolation_is_applied_before_ranking(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        service = app.state.knowledge
        await service.ingest("alice", "alice.txt", "ALICE_SECRET 合成睡眠计划".encode())
        await service.ingest("bob", "bob.txt", "BOB_SECRET 合成睡眠计划".encode())
        await service.ingest(
            "system-public", "public.txt", "公共 合成睡眠计划".encode(), visibility="public"
        )
        alice = (await service.search("alice", "合成睡眠计划")).model_dump_json()
        bob = (await service.search("bob", "合成睡眠计划")).model_dump_json()
        assert "ALICE_SECRET" in alice and "BOB_SECRET" not in alice
        assert "BOB_SECRET" in bob and "ALICE_SECRET" not in bob
        assert "公共" in alice and "公共" in bob
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/documents/text",
                json={"filename": "bad.txt", "text": "合成", "visibility": "public"},
            )
            assert response.status_code == 422


async def test_failed_ingestion_is_visible_without_partial_index(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        result = await app.state.knowledge.ingest("local-user", "broken.pdf", b"not a pdf")
        assert result["parse_status"] == "failed"
        assert result["index_status"] == "not_indexed"
        assert result["error_code"] == "parse_failed"
        assert (await app.state.knowledge.search("local-user", "not a pdf")).data["citations"] == []
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (
                await client.post(
                    "/api/documents/text", json={"filename": "../../bad.txt", "text": "合成"}
                )
            ).status_code == 422
            assert (
                await client.post("/api/documents/text", json={"filename": "x.exe", "text": "合成"})
            ).status_code == 422
