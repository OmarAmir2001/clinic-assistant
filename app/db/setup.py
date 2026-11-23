# app/db/setup.py
"""Create the tables, then add the clinic's doctors and their slots for the next 14 days.

    uv run python -m app.db.setup

Safe to run again: it never adds the same row twice.
"""
import asyncio
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg

from app.core.config import get_settings
from app.core.enums import Weekday
from app.db.connection import check_database
from app.repositories.doctors import DoctorRepository

SCHEMA = Path(__file__).with_name("schema.sql")
CAIRO = ZoneInfo("Africa/Cairo")
DAYS_AHEAD = 14


def next_days(count: int) -> list[date]:
    today = datetime.now(CAIRO).date()
    return [today + timedelta(days=n) for n in range(count)]


async def main() -> None:
    settings = get_settings()
    doctors = DoctorRepository(settings.DOCTORS_PATH).list()

    await check_database(settings)  # wait until PostgreSQL is up
    connection = await asyncpg.connect(settings.database_url)
    try:
        # 1. The tables
        await connection.execute(SCHEMA.read_text(encoding="utf-8"))

        # 2. The doctors. $1, $2 ... are filled in by asyncpg, safely
        for d in doctors:
            await connection.execute(
                "INSERT INTO doctors (id, name, name_ar, specialty, fee_egp) VALUES ($1, $2, $3, $4, $5) "
                "ON CONFLICT (id) DO NOTHING",
                d.id, d.name, d.name_ar, d.specialty.value, d.fee_egp,
            )

        # 3. One slot for every time each doctor works, on each of the next 14 days
        for day in next_days(DAYS_AHEAD):
            weekday = Weekday(day.strftime("%A").lower())   # 2026-11-29 -> "sunday"
            for d in doctors:
                for hhmm in d.schedule.get(weekday, []):     # e.g. ["17:00", "18:00"]
                    starts_at = datetime.combine(day, time.fromisoformat(hhmm), tzinfo=CAIRO)
                    await connection.execute(
                        "INSERT INTO time_slots (doctor_id, starts_at) VALUES ($1, $2) "
                        "ON CONFLICT (doctor_id, starts_at) DO NOTHING",
                        d.id, starts_at,
                    )

        doctor_count = await connection.fetchval("SELECT count(*) FROM doctors")
        slot_count = await connection.fetchval("SELECT count(*) FROM time_slots")
    finally:
        await connection.close()

    print(f"Database ready: {doctor_count} doctors, {slot_count} time slots.")


if __name__ == "__main__":
    asyncio.run(main())
