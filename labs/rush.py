# labs/rush.py
"""Twenty patients press "book" on the same slot at the same moment.

    uv run python -m labs.rush
"""
import asyncio
from collections import Counter

import httpx

from labs.helpers import API, booking, free_slots, new_key

PATIENTS = 20


async def book(client: httpx.AsyncClient, slot_id: int, n: int) -> int:
    response = await client.post("/appointments", json=booking(slot_id, n), headers={"Idempotency-Key": new_key()})
    return response.status_code


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=30, limits=httpx.Limits(max_connections=PATIENTS)) as client:
        [slot] = await free_slots(client)
        # Open all the connections first, so the bookings really leave at the same moment
        await asyncio.gather(*(client.get("/health") for _ in range(PATIENTS)))
        print(f"Slot {slot['slot_id']} ({slot['day']} {slot['time']}): {PATIENTS} bookings at the same moment")
        codes = await asyncio.gather(*(book(client, slot["slot_id"], n) for n in range(PATIENTS)))
    for code, count in sorted(Counter(codes).items()):
        print(f"  {code} {httpx.codes.get_reason_phrase(code):<22} x {count}")


if __name__ == "__main__":
    asyncio.run(main())
