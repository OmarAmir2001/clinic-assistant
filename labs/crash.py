# labs/crash.py
"""A change with two steps fails in the middle. Is anything lost?

    uv run python -m labs.crash
"""
import asyncio

import httpx

from labs.helpers import API, booking, free_slots, new_key

UNREADABLE = ("hours.md", b"   \n\n   \n")  # a new version with no text in it: it can't be read


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=30) as client:
        # 1. Move a booking to a slot someone else just took
        print("1. Move Ahmed's booking to a slot that Sara just took")
        a, b = await free_slots(client, count=2)
        key = {"Idempotency-Key": new_key()}
        ahmed = (await client.post("/appointments", json=booking(a["slot_id"], 3), headers=key)).json()
        await client.post("/appointments", json=booking(b["slot_id"], 4), headers={"Idempotency-Key": new_key()})
        phone = {"X-Patient-Phone": booking(0, 3)["phone"]}
        move = {"slot_id": b["slot_id"]}
        r = await client.post(f"/appointments/{ahmed['reference']}/reschedule", json=move, headers=phone)
        print(f"   reschedule: {r.status_code} {r.json()['error']['message'] if r.status_code >= 400 else ''}")
        r = (await client.get(f"/appointments/{ahmed['reference']}", headers=phone)).json()
        print(f"   Ahmed's booking now: {r['status']}, {r['day']} {r['time']}")

        # 2. Replace a document with a new version that can't be read
        print("2. Replace a document with a new version that can't be read")
        text = f"# Opening hours\n\nThe clinic opens at 9:00 every day except Friday. ({new_key()})\n"
        doc = (await client.post("/documents", files={"file": ("hours.md", text.encode())})).json()
        print(f"   before:  {len((await client.get(f'/documents/{doc['id']}/chunks')).json())} chunk(s)")
        r = await client.put(f"/documents/{doc['id']}", files={"file": UNREADABLE})
        print(f"   replace: {r.status_code} {r.json()['error']['message']}")
        print(f"   after:   {len((await client.get(f'/documents/{doc['id']}/chunks')).json())} chunk(s)")


if __name__ == "__main__":
    asyncio.run(main())
