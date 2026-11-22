# app/repositories/doctors.py
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.enums import Specialty, Weekday


@dataclass(frozen=True)
class Doctor:
    """One doctor and the appointment times they work each week."""
    id: int
    name: str
    name_ar: str
    specialty: Specialty
    fee_egp: int
    schedule: dict[Weekday, list[str]]


class DoctorRepository:
    """Reads the clinic's doctors from data/doctors.json. Session 6 reads them from PostgreSQL."""

    def __init__(self, path: Path):
        rows = json.loads(path.read_text(encoding="utf-8"))
        self._doctors = [
            Doctor(
                id=row["id"],
                name=row["name"],
                name_ar=row["name_ar"],
                specialty=Specialty(row["specialty"]),
                fee_egp=row["fee_egp"],
                schedule={Weekday(day): times for day, times in row["schedule"].items()},
            )
            for row in rows
        ]

    def list(self, specialty: Specialty | None = None, day: Weekday | None = None) -> list[Doctor]:
        doctors = self._doctors
        if specialty is not None:
            doctors = [d for d in doctors if d.specialty == specialty]
        if day is not None:
            doctors = [d for d in doctors if day in d.schedule]
        return doctors

    def get(self, doctor_id: int) -> Doctor | None:
        return next((d for d in self._doctors if d.id == doctor_id), None)
