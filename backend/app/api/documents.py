from fastapi import APIRouter, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.errors import AgentError
from app.auth import UserDependency
from app.rag.parsing import MAX_BYTES, MAX_CHARS, validate_filename

router = APIRouter(prefix="/api/documents", tags=["documents"])


class TextDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    filename: str
    text: str = Field(min_length=1, max_length=MAX_CHARS)

    @field_validator("filename")
    @classmethod
    def text_filename(cls, value):
        validate_filename(value)
        if not value.lower().endswith((".txt", ".md")):
            raise ValueError("text endpoint requires .txt or .md")
        return value


@router.post("/text")
async def ingest_text(body: TextDocumentRequest, request: Request, user_id: UserDependency):
    return await request.app.state.knowledge.ingest(
        user_id, body.filename, body.text.encode("utf-8")
    )


@router.post("/upload")
async def upload_document(file: UploadFile, request: Request, user_id: UserDependency):
    try:
        content = await file.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise AgentError("document_too_large", "文档超过 2 MiB 限制。", 413)
        return await request.app.state.knowledge.ingest(user_id, file.filename or "", content)
    finally:
        await file.close()


@router.get("")
async def list_documents(request: Request, user_id: UserDependency):
    return {"documents": await request.app.state.knowledge.repository.list(user_id)}
