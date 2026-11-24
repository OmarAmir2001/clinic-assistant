# app/db/setup.py
"""Create the tables, then add the clinic's doctors and their slots for the next 14 days.

    uv run python -m app.db.setup

Safe to run again: it never adds the same row twice.
"""
import asyncio
from datetime import date, time, timedelta

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.enums import Weekday
from app.db.database import check_database, make_engine, make_sessions
from app.db.models import Base, Doctor, TimeSlot
from app.repositories.doctors import DoctorRepository

DAYS_AHEAD = 14


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.DATABASE_URL)
    await check_database(engine)

    # 1. The tables: every class that inherits from Base becomes a table, if it isn't there yet
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    doctors = DoctorRepository(settings.DOCTORS_PATH).list()
    async with make_sessions(engine)() as session:
        # 2. The doctors: add the ones that aren't there yet
        for d in doctors:
            if await session.get(Doctor, d.id) is None:
                session.add(Doctor(id=d.id, name=d.name, name_ar=d.name_ar,
                                   specialty=d.specialty.value, fee_egp=d.fee_egp))

        # 3. The slots: one for every hour each doctor works, on each of the next 14 days
        rows = await session.execute(select(TimeSlot.doctor_id, TimeSlot.day, TimeSlot.start_time))
        existing = {tuple(row) for row in rows}
        for offset in range(DAYS_AHEAD):
            day = date.today() + timedelta(days=offset)
            weekday = Weekday(day.strftime("%A").lower())  # 2026-11-29 -> "sunday"
            for d in doctors:
                for hhmm in d.schedule.get(weekday, []):  # e.g. ["17:00", "18:00"]
                    start = time.fromisoformat(hhmm)
                    if (d.id, day, start) not in existing:
                        session.add(TimeSlot(doctor_id=d.id, day=day, start_time=start))

        await session.commit()  # save everything at once

        doctor_count = await session.scalar(select(func.count()).select_from(Doctor))
        slot_count = await session.scalar(select(func.count()).select_from(TimeSlot))
    await engine.dispose()
    print(f"Database ready: {doctor_count} doctors, {slot_count} time slots.")


if __name__ == "__main__":
    asyncio.run(main())
