# labs/upload_docs.py
"""Upload every file in data/clinic_docs/ (the reception's documents) to the running API.

    uv run python -m labs.upload_docs
"""
import asyncio
from pathlib import Path

import httpx

from labs.helpers import API

FOLDER = Path("data/clinic_docs")


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=120) as client:
        for path in sorted(FOLDER.iterdir()):
            r = await client.post("/documents", files={"file": (path.name, path.read_bytes())})
            body = r.json()
            chunks = body.get("chunks", body.get("error", {}).get("message"))
            print(f"  {r.status_code}  {path.name:<28} {chunks} chunks")
        total = sum(d["chunks"] for d in (await client.get("/documents")).json())
        print(f"{total} chunks in the database")


if __name__ == "__main__":
    asyncio.run(main())
