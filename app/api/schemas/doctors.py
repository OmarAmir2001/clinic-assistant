# app/api/schemas/doctors.py
from pydantic import BaseModel

from app.core.enums import Specialty, Weekday


class DoctorOut(BaseModel):
    id: int
    name: str
    specialty: Specialty
    fee_egp: int
    days: list[Weekday]


class FreeSlotsOut(BaseModel):
    doctor_id: int
    day: Weekday
    free_times: list[str]
