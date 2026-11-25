# labs/helpers.py
"""What every lab needs: where the API is, a free slot, and a fresh key."""
import uuid
from datetime import date, timedelta

import httpx

API = "http://127.0.0.1:8000"


async def free_slots(client: httpx.AsyncClient, doctor_id: int = 1, count: int = 1) -> list[dict]:
    """The first free slots of this doctor in the next 14 days, with their day."""
    found = []
    for offset in range(14):
        day = (date.today() + timedelta(days=offset)).isoformat()
        response = await client.get(f"/doctors/{doctor_id}/slots", params={"day": day})
        found += [{**slot, "day": day} for slot in response.json()["slots"]]
        if len(found) >= count:
            return found[:count]
    raise SystemExit("No free slots left. Run: uv run python -m app.db.setup (or reset the database)")


def new_key() -> str:
    return str(uuid.uuid4())


def booking(slot_id: int, n: int = 0) -> dict:
    return {"slot_id": slot_id, "patient_name": f"Lab Patient {n}", "phone": f"0100000{n:04d}"}
