# app/db/break_it.py
"""Try to put bad bookings into the database, and see what it says.

    uv run python -m app.db.break_it
"""
import asyncio

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.database import make_engine, make_sessions
from app.db.models import Appointment

PATIENT = {"patient_name": "Test Patient", "phone": "01000000000"}
ATTEMPTS = [
    ("1. A normal booking for slot 1", {"reference": "NFC-TEST01", "slot_id": 1}),
    ("2. Someone else books slot 1", {"reference": "NFC-TEST02", "slot_id": 1}),
    ("3. A booking for slot 999999", {"reference": "NFC-TEST03", "slot_id": 999999}),
    ("4. A status of 'maybe'", {"reference": "NFC-TEST04", "slot_id": 2, "status": "maybe"}),
]


def short(error: IntegrityError) -> str:
    """The database's own message, first line only."""
    message = str(error.orig).splitlines()[0]
    return message.split(">: ", 1)[-1]  # PostgreSQL's message starts with "<class '...'>: "


async def main() -> None:
    engine = make_engine(get_settings().DATABASE_URL)
    sessions = make_sessions(engine)

    async with sessions() as session:  # start clean: remove the test bookings of an earlier run
        await session.execute(delete(Appointment).where(Appointment.reference.like("NFC-TEST%")))
        await session.commit()

    for label, values in ATTEMPTS:
        async with sessions() as session:
            session.add(Appointment(**values, **PATIENT))
            try:
                await session.commit()
                print(f"{label:<32} accepted")
            except IntegrityError as error:
                print(f"{label:<32} REFUSED: {short(error)}")

    async with sessions() as session:  # 5. Cancel booking 1: now slot 1 can be booked again
        first = update(Appointment).where(Appointment.reference == "NFC-TEST01")
        await session.execute(first.values(status="cancelled"))
        session.add(Appointment(reference="NFC-TEST05", slot_id=1, **PATIENT))
        await session.commit()
        print(f"{'5. Cancel 1, then book slot 1':<32} accepted")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
