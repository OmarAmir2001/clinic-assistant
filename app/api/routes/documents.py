# app/api/routes/documents.py
from typing import Annotated

from fastapi import APIRouter, Path, UploadFile, status

from app.api.dependencies import IngestionServiceDep
from app.api.schemas.documents import DOCUMENT_ID_PATTERN, ChunkOut, DocumentOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.repositories.documents import Document

router = APIRouter(prefix="/documents", tags=["documents"], responses=INVALID_INPUT)

DocumentId = Annotated[str, Path(pattern=DOCUMENT_ID_PATTERN, description="The id from POST /documents")]


def to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        name=document.name,
        type=document.type,
        size_bytes=document.size_bytes,
        pages=document.pages,
        chunks=document.chunk_count,
        warnings=list(document.warnings),
        uploaded_at=document.uploaded_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        413: {"model": ErrorResponse, "description": "The file is too big"},
        415: {"model": ErrorResponse, "description": "Not a PDF, TXT or MD file, or the content doesn't match"},
    },
)
def upload_document(file: UploadFile, service: IngestionServiceDep) -> DocumentOut:
    """Upload a clinic document (PDF, TXT or MD). It is checked, read, cleaned and cut into chunks."""
    # A plain `def`: reading PDFs is slow work, so FastAPI runs it in a worker thread
    return to_out(service.ingest(file.filename, file.file))


@router.get("")
def list_documents(service: IngestionServiceDep) -> list[DocumentOut]:
    """Every document uploaded since the server started."""
    return [to_out(d) for d in service.list_documents()]


@router.get("/{document_id}/chunks", responses={404: {"model": ErrorResponse, "description": "No such document"}})
def get_chunks(document_id: DocumentId, service: IngestionServiceDep) -> list[ChunkOut]:
    """The chunks one document was cut into, in order."""
    return [
        ChunkOut(index=c.index, text=c.text, characters=len(c.text), page=c.page, section=c.section)
        for c in service.get_chunks(document_id)
    ]
