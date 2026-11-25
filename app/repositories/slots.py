# app/repositories/slots.py
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Appointment, TimeSlot


class SlotRepository:
    """Every database question about time slots."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def free(self, doctor_id: int, day: date) -> list[TimeSlot]:
        # A slot is free when no BOOKED appointment points at it.
        # LEFT OUTER JOIN keeps every slot; the ones with no booked appointment get NULLs, and we keep those.
        query = (
            select(TimeSlot)
            .outerjoin(Appointment, Appointment.slot_id == TimeSlot.id)
            .where(TimeSlot.doctor_id == doctor_id, TimeSlot.day == day, Appointment.id.is_(None))
            .order_by(TimeSlot.start_time)
        )
        return list(await self.session.scalars(query))

    async def lock(self, slot_id: int) -> TimeSlot | None:
        # SELECT ... FOR UPDATE: lock this slot's row until our transaction ends.
        # Anyone else locking the same slot waits here until we commit or roll back.
        query = select(TimeSlot).where(TimeSlot.id == slot_id).with_for_update()
        return await self.session.scalar(query)
