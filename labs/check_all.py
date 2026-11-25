# labs/check_all.py
"""Walk through the whole API once and check every promise it makes (Checkpoint 1).

    uv run python -m labs.check_all
"""
import asyncio

import httpx

from labs.helpers import API, booking, free_slots, new_key

results: list[bool] = []


def check(promise: str, ok: bool) -> None:
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {promise}")


async def is_free(client: httpx.AsyncClient, slot: dict) -> bool:
    response = await client.get("/doctors/2/slots", params={"day": slot["day"]})
    return slot["slot_id"] in [s["slot_id"] for s in response.json()["slots"]]


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=30) as client:
        print("Booking")
        a, b = await free_slots(client, doctor_id=2, count=2)
        key, body = new_key(), booking(a["slot_id"], 7)
        phone = {"X-Patient-Phone": body["phone"]}
        r = await client.post("/appointments", json=body, headers={"Idempotency-Key": key})
        check("a free slot can be booked (201)", r.status_code == 201)
        ref = r.json()["reference"]
        check("the booked slot is no longer free", not await is_free(client, a))
        again = await client.post("/appointments", json=body, headers={"Idempotency-Key": key})
        check("the same key gives back the same booking", again.json().get("reference") == ref)
        other_key = {"Idempotency-Key": new_key()}
        other = await client.post("/appointments", json=booking(a["slot_id"], 8), headers=other_key)
        check("someone else can't book the same slot (409)", other.status_code == 409)
        r = await client.get(f"/appointments/{ref}", headers=phone)
        check("the patient can see the booking", r.status_code == 200)
        r = await client.get(f"/appointments/{ref}", headers={"X-Patient-Phone": "01099999999"})
        check("another phone can't see it (404)", r.status_code == 404)

        print("Rescheduling")
        r = await client.post(f"/appointments/{ref}/reschedule", json={"slot_id": b["slot_id"]}, headers=phone)
        check("a booking can move to a free slot", r.status_code == 200 and r.json()["time"] == b["time"])
        check("the old slot is free again", await is_free(client, a))
        check("the new slot is taken", not await is_free(client, b))

        print("Cancelling")
        r = await client.delete(f"/appointments/{ref}", headers=phone)
        check("a booking can be cancelled (204)", r.status_code == 204)
        r = await client.delete(f"/appointments/{ref}", headers=phone)
        check("cancelling twice is harmless (204)", r.status_code == 204)
        check("a cancelled booking frees its slot", await is_free(client, b))
        r = await client.post(f"/appointments/{ref}/reschedule", json={"slot_id": a["slot_id"]}, headers=phone)
        check("a cancelled booking can't be moved (409)", r.status_code == 409)

        print("Documents")
        text = f"# Parking\n\nFree parking behind the clinic. ({new_key()})\n".encode()
        r = await client.post("/documents", files={"file": ("parking.md", text)})
        check("a document can be uploaded (201)", r.status_code == 201)
        doc = r.json()["id"]
        r = await client.post("/documents", files={"file": ("parking.md", text)})
        check("the same file again gives back the same document (200)", r.status_code == 200 and r.json()["id"] == doc)
        longer = text + b"\n## Bikes\n\nBike racks are next to the entrance.\n"
        r = await client.put(f"/documents/{doc}", files={"file": ("parking.md", longer)})
        check("a document can be replaced with a new version", r.status_code == 200 and r.json()["chunks"] == 2)
        r = await client.put(f"/documents/{doc}", files={"file": ("parking.md", b"  \n ")})
        chunks = (await client.get(f"/documents/{doc}/chunks")).json()
        check("an unreadable new version changes nothing", r.status_code == 422 and len(chunks) == 2)

    print(f"{sum(results)} of {len(results)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
