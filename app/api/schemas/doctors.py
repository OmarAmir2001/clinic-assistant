# app/api/schemas/doctors.py
from datetime import date

from pydantic import BaseModel

from app.core.enums import Specialty


class DoctorOut(BaseModel):
    id: int
    name: str
    name_ar: str
    specialty: Specialty
    fee_egp: int


class SlotOut(BaseModel):
    slot_id: int  # what you send to POST /appointments
    time: str  # like 17:00


class FreeSlotsOut(BaseModel):
    doctor_id: int
    day: date
    slots: list[SlotOut]
