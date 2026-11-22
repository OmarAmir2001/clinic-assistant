# app/services/file_checks.py
"""Checks for uploaded files. Everything about the file comes from outside, so nothing is trusted."""
import re
from pathlib import Path, PurePosixPath

from app.core.enums import DocumentType
from app.core.errors import EmptyDocumentError, UnsupportedFileError

# Letters (any language), digits, dot, dash, underscore and space. Anything else becomes "_"
UNSAFE_CHARACTERS = re.compile(r"[^\w.\- ]")
MAX_NAME_LENGTH = 100


def safe_display_name(filename: str | None) -> str:
    """A clean name to SHOW people. It is never used as a path on disk."""
    # Keep only the last part: "../../app/main.py" and "C:\\Windows\\x.txt" become "main.py" and "x.txt"
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    name = UNSAFE_CHARACTERS.sub("_", name).strip(" .")
    return name[:MAX_NAME_LENGTH] or "document"


def detect_type(name: str) -> DocumentType:
    """The file type comes from its extension, checked against an allowlist."""
    extension = Path(name).suffix.lower().lstrip(".")
    try:
        return DocumentType(extension)
    except ValueError:
        allowed = ", ".join(t.upper() for t in DocumentType)
        raise UnsupportedFileError(f"Only {allowed} files are accepted.") from None


def check_content(path: Path, doc_type: DocumentType) -> None:
    """The name is a claim. Look inside the file to check it really is what it says."""
    with path.open("rb") as file:
        start = file.read(1024)
    if not start:
        raise EmptyDocumentError("The file is empty.")

    if doc_type is DocumentType.PDF:
        # Every PDF file starts with these five bytes
        if not start.startswith(b"%PDF-"):
            raise UnsupportedFileError("This file is named .pdf, but it is not a PDF.")
        return

    # TXT and MD: must be readable text in UTF-8, with no zero bytes (those mean a binary file)
    data = path.read_bytes()
    if b"\x00" in data:
        raise UnsupportedFileError(f"This file is named .{doc_type}, but it is not a text file.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise UnsupportedFileError("Text files must be saved as UTF-8.") from None
