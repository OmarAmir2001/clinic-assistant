# app/repositories/files.py
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.errors import FileTooLargeError

# Read and write 64 KB at a time, so a big file never sits in memory all at once
BLOCK_SIZE = 64 * 1024


@dataclass(frozen=True)
class StoredFile:
    path: Path
    size_bytes: int
    sha256: str


class FileStore:
    """The only code that writes uploaded files to disk. Every file gets a new random name."""

    def __init__(self, folder: Path, max_bytes: int):
        self.folder = folder
        self.max_bytes = max_bytes
        self.folder.mkdir(parents=True, exist_ok=True)

    def save(self, content: BinaryIO, suffix: str) -> StoredFile:
        # The name on disk is ours, never the uploader's: no "../", no overwriting other files
        path = self.folder / f"{uuid.uuid4().hex}{suffix}"
        size, digest = 0, hashlib.sha256()
        try:
            with path.open("xb") as out:  # "x": fail rather than overwrite an existing file
                while block := content.read(BLOCK_SIZE):
                    size += len(block)
                    if size > self.max_bytes:
                        limit_mb = self.max_bytes // (1024 * 1024)
                        raise FileTooLargeError(f"The file is bigger than the {limit_mb} MB limit.")
                    digest.update(block)
                    out.write(block)
        except Exception:
            path.unlink(missing_ok=True)  # never leave half a file behind
            raise
        return StoredFile(path=path, size_bytes=size, sha256=digest.hexdigest())

    def delete(self, path: Path) -> None:
        path.unlink(missing_ok=True)
