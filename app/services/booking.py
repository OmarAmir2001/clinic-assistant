# app/services/booking.py
import logging
import secrets

from app.core.enums import Specialty, Weekday
from app.core.errors import ConflictError, NotFoundError
from app.repositories.appointments import Appointment, InMemoryAppointmentRepository
from app.repositories.doctors import Doctor, DoctorRepository

logger = logging.getLogger(__name__)


class BookingService:
    """Doctors, free slots and appointments: the clinic's booking rules live here."""

    def __init__(self, doctors: DoctorRepository, appointments: InMemoryAppointmentRepository):
        self.doctors = doctors
        self.appointments = appointments

    def list_doctors(self, specialty: Specialty | None = None, day: Weekday | None = None) -> list[Doctor]:
        return self.doctors.list(specialty=specialty, day=day)

    def get_doctor(self, doctor_id: int) -> Doctor:
        doctor = self.doctors.get(doctor_id)
        if doctor is None:
            raise NotFoundError(f"There is no doctor with id {doctor_id}.")
        return doctor

    def free_slots(self, doctor_id: int, day: Weekday) -> list[str]:
        doctor = self.get_doctor(doctor_id)
        taken = self.appointments.taken_times(doctor_id, day)
        return [time for time in doctor.schedule.get(day, []) if time not in taken]

    def book(self, doctor_id: int, day: Weekday, time: str, patient_name: str, phone: str) -> Appointment:
        doctor = self.get_doctor(doctor_id)
        if time not in doctor.schedule.get(day, []):
            raise NotFoundError(f"{doctor.name} has no appointment slot on {day.title()} at {time}.")
        if time in self.appointments.taken_times(doctor_id, day):
            raise ConflictError(f"{doctor.name} is already booked on {day.title()} at {time}.")

        appointment = Appointment(
            reference=f"NFC-{secrets.token_hex(3).upper()}",
            doctor_id=doctor_id,
            day=day,
            time=time,
            patient_name=patient_name,
            phone=phone,
        )
        self.appointments.add(appointment)
        # Log the reference only: never the patient's name or phone (constraint C-4)
        logger.info("Appointment %s booked", appointment.reference)
        return appointment

    def get_appointment(self, reference: str, phone: str) -> Appointment:
        appointment = self.appointments.get(reference)
        # Same answer for "doesn't exist" and "not yours", so nobody can guess references
        if appointment is None or appointment.phone != phone:
            raise NotFoundError(f"There is no appointment {reference} for this phone number.")
        return appointment

    def cancel(self, reference: str, phone: str) -> None:
        appointment = self.get_appointment(reference, phone)
        self.appointments.delete(appointment.reference)
        logger.info("Appointment %s cancelled", reference)
