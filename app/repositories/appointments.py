# app/repositories/appointments.py
from dataclasses import dataclass

from app.core.enums import Weekday


@dataclass(frozen=True)
class Appointment:
    """One booked appointment."""
    reference: str
    doctor_id: int
    day: Weekday
    time: str
    patient_name: str
    phone: str


class InMemoryAppointmentRepository:
    """Keeps appointments in a dictionary. A restart loses them all: Session 6 moves them to PostgreSQL."""

    def __init__(self):
        self._by_reference: dict[str, Appointment] = {}

    def add(self, appointment: Appointment) -> None:
        self._by_reference[appointment.reference] = appointment

    def get(self, reference: str) -> Appointment | None:
        return self._by_reference.get(reference)

    def delete(self, reference: str) -> None:
        self._by_reference.pop(reference, None)

    def taken_times(self, doctor_id: int, day: Weekday) -> set[str]:
        return {a.time for a in self._by_reference.values() if a.doctor_id == doctor_id and a.day == day}
