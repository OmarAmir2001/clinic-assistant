# app/repositories/doctors.py
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AppointmentStatus, Specialty
from app.db.models import Appointment, Doctor, TimeSlot


class DoctorRepository:
    """Every database question about doctors. Nobody else writes SQL about them."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, specialty: Specialty | None = None, free_on: date | None = None) -> list[Doctor]:
        query = select(Doctor).order_by(Doctor.id)
        if specialty is not None:
            query = query.where(Doctor.specialty == specialty)
        if free_on is not None:
            # Only doctors with at least one free slot that day (a JOIN, then the free-slot rule)
            query = (
                query.join(TimeSlot, TimeSlot.doctor_id == Doctor.id)
                .outerjoin(
                    Appointment,
                    (Appointment.slot_id == TimeSlot.id) & (Appointment.status == AppointmentStatus.BOOKED),
                )
                .where(TimeSlot.day == free_on, Appointment.id.is_(None))
                .distinct()
            )
        return list(await self.session.scalars(query))

    async def get(self, doctor_id: int) -> Doctor | None:
        return await self.session.get(Doctor, doctor_id)
