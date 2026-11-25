# labs/retry.py
"""The same request arrives more than once: a retry after a timeout, a double click, an upload sent twice.

    uv run python -m labs.retry
"""
import asyncio

import httpx

from labs.helpers import API, booking, free_slots, new_key

NAME = "visiting_hours.md"


async def main() -> None:
    # A fresh connection for every request: a server error can't break the next request
    fresh = httpx.Limits(max_keepalive_connections=0)
    async with httpx.AsyncClient(base_url=API, timeout=30, limits=fresh) as client:
        first, second = await free_slots(client, count=2)

        # 1. The app didn't hear back, so it sends the same booking again, with the same key
        print("1. The same booking sent twice, one after the other (same Idempotency-Key)")
        key, body = new_key(), booking(first["slot_id"], 1)
        for attempt in (1, 2):
            r = await client.post("/appointments", json=body, headers={"Idempotency-Key": key})
            print(f"   attempt {attempt}: {r.status_code} {r.json().get('reference') or r.json()['error']['message']}")

        # 2. A double click: the same request five times at the same moment
        print("2. The same booking five times at the same moment (a double click)")
        key, body = new_key(), booking(second["slot_id"], 2)
        replies = await asyncio.gather(
            *(client.post("/appointments", json=body, headers={"Idempotency-Key": key}) for _ in range(5))
        )
        for r in replies:
            print(f"   {r.status_code} {r.json().get('reference') or r.json()['error']['message']}")

        # 3. The same file uploaded twice (new text each run, so the first upload is really new)
        print(f"3. The same file uploaded twice ({NAME})")
        text = f"# Visiting hours\n\nVisitors are welcome from 10:00 to 20:00. ({new_key()})\n".encode()
        for attempt in (1, 2):
            r = await client.post("/documents", files={"file": (NAME, text)})
            print(f"   attempt {attempt}: {r.status_code} {r.json().get('id') or r.json()['error']['message']}")
        listing = (await client.get("/documents")).json()
        copies = sum(d["name"] == NAME and d["size_bytes"] == len(text) for d in listing)
        print(f"   documents with this text: {copies}")


if __name__ == "__main__":
    asyncio.run(main())
