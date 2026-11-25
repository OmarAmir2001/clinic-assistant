# app/services/booking.py
import logging
import secrets
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AppointmentStatus, Specialty
from app.core.errors import ConflictError, NotFoundError
from app.db.models import Appointment, Doctor, TimeSlot
from app.repositories.appointments import AppointmentRepository
from app.repositories.doctors import DoctorRepository
from app.repositories.slots import SlotRepository

logger = logging.getLogger(__name__)


class BookingService:
    """Doctors, free slots and appointments: the clinic's booking rules live here.

    Every method that writes starts its transaction first: `async with self.session.begin():`.
    Inside it, everything is saved together at the end, or nothing is.
    """

    def __init__(
        self,
        session: AsyncSession,
        doctors: DoctorRepository,
        slots: SlotRepository,
        appointments: AppointmentRepository,
    ):
        self.session = session
        self.doctors = doctors
        self.slots = slots
        self.appointments = appointments

    async def list_doctors(self, specialty: Specialty | None = None, free_on: date | None = None) -> list[Doctor]:
        return await self.doctors.list(specialty=specialty, free_on=free_on)

    async def get_doctor(self, doctor_id: int) -> Doctor:
        doctor = await self.doctors.get(doctor_id)
        if doctor is None:
            raise NotFoundError(f"There is no doctor with id {doctor_id}.")
        return doctor

    async def free_slots(self, doctor_id: int, day: date) -> list[TimeSlot]:
        await self.get_doctor(doctor_id)
        return await self.slots.free(doctor_id, day)

    async def book(self, slot_id: int, patient_name: str, phone: str, idempotency_key: str) -> Appointment:
        try:
            async with self.session.begin():
                # 1. Lock the slot. Anyone else booking it waits on this line until we commit
                slot = await self.slots.lock(slot_id)
                if slot is None:
                    raise NotFoundError(f"There is no time slot {slot_id}.")

                # 2. Is this a retry of a request we already handled? Give back the same booking
                earlier = await self.appointments.get_by_key(idempotency_key)
                if earlier is not None:
                    return self._same_request(earlier, slot_id, phone)

                # 3. Now the check is safe: nobody can book this slot between our check and our insert
                if await self.appointments.is_booked(slot_id):
                    raise ConflictError("This time slot is already booked. Please choose another one.")

                appointment = Appointment(
                    reference=f"NFC-{secrets.token_hex(3).upper()}",
                    slot_id=slot_id,
                    patient_name=patient_name,
                    phone=phone,
                    idempotency_key=idempotency_key,
                )
                self.appointments.add(appointment)
            # 4. Leaving the block commits: the booking is saved and the lock is released
        except IntegrityError:
            # The same key arrived twice at the same moment (a double click): the other copy won
            earlier = await self.appointments.get_by_key(idempotency_key)
            if earlier is None:
                raise
            return self._same_request(earlier, slot_id, phone)

        # Log the reference only: never the patient's name or phone (constraint C-4)
        logger.info("Appointment %s booked", appointment.reference)
        return await self.appointments.get(appointment.reference)

    def _same_request(self, earlier: Appointment, slot_id: int, phone: str) -> Appointment:
        if earlier.slot_id != slot_id or earlier.phone != phone:
            raise ConflictError("This Idempotency-Key was already used for a different booking.")
        logger.info("Repeated request for appointment %s: returning the same booking", earlier.reference)
        return earlier

    async def get_appointment(self, reference: str, phone: str) -> Appointment:
        appointment = await self.appointments.get(reference)
        # Same answer for "doesn't exist" and "not yours", so nobody can guess references
        if appointment is None or appointment.phone != phone:
            raise NotFoundError(f"There is no appointment {reference} for this phone number.")
        return appointment

    async def cancel(self, reference: str, phone: str) -> None:
        async with self.session.begin():
            appointment = await self.appointments.lock(reference)
            if appointment is None or appointment.phone != phone:
                raise NotFoundError(f"There is no appointment {reference} for this phone number.")
            # Cancelling twice is fine: the second time there's nothing left to do
            appointment.status = AppointmentStatus.CANCELLED
        logger.info("Appointment %s cancelled", reference)

    async def reschedule(self, reference: str, phone: str, new_slot_id: int) -> Appointment:
        async with self.session.begin():
            # 1. Lock the booking, then the new slot (always in this order)
            appointment = await self.appointments.lock(reference)
            if appointment is None or appointment.phone != phone:
                raise NotFoundError(f"There is no appointment {reference} for this phone number.")
            if appointment.status != AppointmentStatus.BOOKED:
                raise ConflictError("This appointment was cancelled; please book a new one.")
            if appointment.slot_id != new_slot_id:
                new_slot = await self.slots.lock(new_slot_id)
                if new_slot is None:
                    raise NotFoundError(f"There is no time slot {new_slot_id}.")
                if await self.appointments.is_booked(new_slot_id):
                    raise ConflictError("The new time slot is already booked. Your appointment was not changed.")
                # 2. One UPDATE moves the booking: the old slot is freed and the new one taken at the same moment
                appointment.slot_id = new_slot_id
        logger.info("Appointment %s moved to slot %d", reference, new_slot_id)
        self.session.expunge_all()  # forget the old copy, so the next line reads the new slot from the database
        return await self.appointments.get(reference)
