# app/api/routes/documents.py
import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Response, UploadFile, status

from app.api.dependencies import IngestionServiceDep
from app.api.schemas.documents import DOCUMENT_ID_PATTERN, ChunkOut, DocumentOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.repositories.documents import DocumentInfo

router = APIRouter(prefix="/documents", tags=["documents"], responses=INVALID_INPUT)

DocumentId = Annotated[str, Path(pattern=DOCUMENT_ID_PATTERN, description="The id from POST /documents")]
FILE_ERRORS = {
    413: {"model": ErrorResponse, "description": "The file is too big"},
    415: {"model": ErrorResponse, "description": "Not a PDF, TXT or MD file, or the content doesn't match"},
}


def to_out(info: DocumentInfo) -> DocumentOut:
    document = info.document
    return DocumentOut(
        id=document.id.hex,
        name=document.name,
        type=document.type,
        size_bytes=document.size_bytes,
        pages=info.pages,
        chunks=info.chunks,
        warnings=info.warnings,
        uploaded_at=document.uploaded_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "We already had this file"}, **FILE_ERRORS},
)
async def upload_document(file: UploadFile, response: Response, service: IngestionServiceDep) -> DocumentOut:
    """Upload a clinic document (PDF, TXT or MD). It is checked, read, cleaned, cut into chunks and saved.

    Uploading the same file again gives back the document we already have (200), never a copy.
    """
    info, created = await service.ingest(file.filename, file.file)
    if not created:
        response.status_code = status.HTTP_200_OK
    return to_out(info)


@router.put(
    "/{document_id}",
    responses={404: {"model": ErrorResponse, "description": "No such document"}, **FILE_ERRORS},
)
async def replace_document(document_id: DocumentId, file: UploadFile, service: IngestionServiceDep) -> DocumentOut:
    """Replace a document with a new version. If the new file can't be read, the old version stays untouched."""
    return to_out(await service.replace(uuid.UUID(document_id), file.filename, file.file))


@router.get("")
async def list_documents(service: IngestionServiceDep) -> list[DocumentOut]:
    """Every document in the database."""
    return [to_out(info) for info in await service.list_documents()]


@router.get("/{document_id}/chunks", responses={404: {"model": ErrorResponse, "description": "No such document"}})
async def get_chunks(document_id: DocumentId, service: IngestionServiceDep) -> list[ChunkOut]:
    """The chunks one document was cut into, in order."""
    return [
        ChunkOut(index=c.position, text=c.text, characters=len(c.text), page=c.page, section=c.section)
        for c in await service.get_chunks(uuid.UUID(document_id))
    ]
