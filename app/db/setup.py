# app/db/setup.py
"""Create the tables, then fill them with the clinic's doctors and their next two weeks of slots.

    uv run python -m app.db.setup

Run it as often as you like: it never creates the same row twice.
"""
import asyncio
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg

from app.core.config import get_settings
from app.core.enums import Weekday
from app.repositories.doctors import Doctor, DoctorRepository

SCHEMA = Path(__file__).with_name("schema.sql")

# date.weekday() counts from Monday = 0; our Weekday enum uses names
WEEKDAY_OF = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY,
              Weekday.FRIDAY, Weekday.SATURDAY, Weekday.SUNDAY]


def build_slots(doctors: list[Doctor], first_day: date, days: int, minutes: int,
                zone: ZoneInfo) -> list[tuple[int, datetime, datetime]]:
    """Turn each doctor's weekly times ("sunday 17:00") into real slots on real dates."""
    slots = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        weekday = WEEKDAY_OF[day.weekday()]
        for doctor in doctors:
            for hhmm in doctor.schedule.get(weekday, []):
                # The clinic's local time, stored with its time zone so it means one moment
                starts = datetime.combine(day, time.fromisoformat(hhmm), tzinfo=zone)
                slots.append((doctor.id, starts, starts + timedelta(minutes=minutes)))
    return slots


async def main() -> None:
    settings = get_settings()
    doctors = DoctorRepository(settings.DOCTORS_PATH).list()
    today = datetime.now(settings.CLINIC_TIMEZONE).date()
    slots = build_slots(doctors, today, settings.SCHEDULE_DAYS, settings.SLOT_MINUTES, settings.CLINIC_TIMEZONE)

    connection = await asyncpg.connect(settings.database_url)
    try:
        # All or nothing: if any step fails, none of it is kept
        async with connection.transaction():
            await connection.execute(SCHEMA.read_text(encoding="utf-8"))

            # A doctor that already exists gets the latest details from doctors.json
            await connection.executemany(
                """
                INSERT INTO doctors (id, name, name_ar, specialty, fee_egp)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name, name_ar = EXCLUDED.name_ar,
                    specialty = EXCLUDED.specialty, fee_egp = EXCLUDED.fee_egp
                """,
                [(d.id, d.name, d.name_ar, d.specialty.value, d.fee_egp) for d in doctors],
            )
            # A slot that already exists is left alone (it may already be booked)
            await connection.executemany(
                """
                INSERT INTO time_slots (doctor_id, starts_at, ends_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (doctor_id, starts_at) DO NOTHING
                """,
                slots,
            )

        counts = await connection.fetchrow(
            "SELECT (SELECT count(*) FROM doctors) AS doctors, (SELECT count(*) FROM time_slots) AS slots"
        )
    finally:
        await connection.close()

    print(f"Database {settings.database_place} is ready: {counts['doctors']} doctors, {counts['slots']} time slots.")


if __name__ == "__main__":
    asyncio.run(main())
