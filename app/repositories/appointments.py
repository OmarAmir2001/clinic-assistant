# app/repositories/appointments.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import AppointmentStatus
from app.db.models import Appointment, TimeSlot

# Load the slot and its doctor in the same query: in async code nothing may be loaded "later, by surprise"
WITH_SLOT_AND_DOCTOR = joinedload(Appointment.slot).joinedload(TimeSlot.doctor)


class AppointmentRepository:
    """Every database question about appointments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, appointment: Appointment) -> None:
        self.session.add(appointment)  # saved when the transaction commits

    async def get(self, reference: str) -> Appointment | None:
        query = select(Appointment).where(Appointment.reference == reference).options(WITH_SLOT_AND_DOCTOR)
        return await self.session.scalar(query)

    async def get_by_key(self, idempotency_key: str) -> Appointment | None:
        query = select(Appointment).where(Appointment.idempotency_key == idempotency_key).options(WITH_SLOT_AND_DOCTOR)
        return await self.session.scalar(query)

    async def lock(self, reference: str) -> Appointment | None:
        # Lock the booking's row: no one else can cancel or move it until we finish
        query = select(Appointment).where(Appointment.reference == reference).with_for_update()
        return await self.session.scalar(query)

    async def is_booked(self, slot_id: int) -> bool:
        query = select(Appointment.id).where(
            Appointment.slot_id == slot_id, Appointment.status == AppointmentStatus.BOOKED
        )
        return await self.session.scalar(query) is not None
