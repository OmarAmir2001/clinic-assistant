# app/services/loaders.py
"""Turn a stored file into blocks of text, keeping where each block came from (page or section)."""
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.enums import DocumentType
from app.core.errors import UnsupportedFileError

# A plain-text heading: a short line in capital letters, like "INSURANCE"
TXT_HEADING = re.compile(r"^[A-Z][A-Z ,&\-]{2,60}$")


@dataclass(frozen=True)
class TextBlock:
    text: str
    page: int | None = None      # PDFs only, counting from 1
    section: str | None = None   # the heading the text sits under, if the file has headings


def load_pdf(path: Path, max_pages: int) -> list[TextBlock]:
    """One block per page. Only this file knows we use PyMuPDF."""
    with pymupdf.open(path) as pdf:
        if pdf.needs_pass:
            raise UnsupportedFileError("Password-protected PDFs are not accepted.")
        if pdf.page_count > max_pages:
            raise UnsupportedFileError(f"The PDF has {pdf.page_count} pages; the limit is {max_pages}.")
        return [TextBlock(text=page.get_text(), page=number) for number, page in enumerate(pdf, start=1)]


def load_markdown(path: Path) -> list[TextBlock]:
    """One block per heading. The heading line stays in the block, so every chunk knows its topic."""
    return _split_by_headings(path.read_text(encoding="utf-8"), lambda line: line.startswith("#"),
                              lambda line: line.lstrip("#").strip())


def load_text(path: Path) -> list[TextBlock]:
    """Plain text has no heading marks, so we treat a short line in capitals as a heading."""
    return _split_by_headings(path.read_text(encoding="utf-8"), lambda line: bool(TXT_HEADING.match(line)),
                              lambda line: line.strip().title())


def _split_by_headings(text, is_heading, heading_name) -> list[TextBlock]:
    blocks, section, lines = [], None, []
    for line in text.splitlines():
        if is_heading(line.strip()) and lines:
            blocks.append(TextBlock(text="\n".join(lines), section=section))
            lines = []
        if is_heading(line.strip()):
            section = heading_name(line.strip())
        lines.append(line)
    if lines:
        blocks.append(TextBlock(text="\n".join(lines), section=section))
    return blocks


def load_document(path: Path, doc_type: DocumentType, max_pages: int) -> list[TextBlock]:
    if doc_type is DocumentType.PDF:
        return load_pdf(path, max_pages)
    if doc_type is DocumentType.MD:
        return load_markdown(path)
    return load_text(path)
