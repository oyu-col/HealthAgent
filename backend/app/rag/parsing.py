import io
import logging
from pathlib import PurePath

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

MAX_BYTES = 2 * 1024 * 1024
MAX_CHARS = 200_000


def validate_filename(filename):
    if (
        not filename
        or len(filename) > 200
        or any(c in filename for c in ("/", "\\", ":", "\x00", "\r", "\n"))
    ):
        raise ValueError("invalid filename")
    if PurePath(filename).suffix.lower() not in {".txt", ".md", ".pdf"}:
        raise ValueError("unsupported file type")
    return filename


def parse_and_split(filename: str, content: bytes):
    validate_filename(filename)
    if not content or len(content) > MAX_BYTES:
        raise ValueError("empty or oversized document")
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf":
        # pypdf diagnostics can include the first bytes of malformed private uploads.
        logging.getLogger("pypdf").setLevel(logging.CRITICAL)
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) > 50:
            raise ValueError("encrypted or too many pages")
        pages = []
        total_chars = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            total_chars += len(text)
            if total_chars > MAX_CHARS:
                raise ValueError("too much extracted text")
            pages.append(Document(page_content=text, metadata={"page": number}))
    else:
        text = content.decode("utf-8-sig")
        if len(text) > MAX_CHARS:
            raise ValueError("too much text")
        pages = [Document(page_content=text, metadata={"page": 1})]
    if not any(page.page_content.strip() for page in pages):
        raise ValueError("no extractable text; OCR is not supported")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        add_start_index=True,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    if len(chunks) > 500:
        raise ValueError("too many chunks")
    return chunks
