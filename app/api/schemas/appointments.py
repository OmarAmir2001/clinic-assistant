# app/api/schemas/appointments.py
from pydantic import BaseModel, Field

from app.core.enums import Weekday

# An Egyptian mobile number: 010, 011, 012 or 015, then 8 digits
PHONE_PATTERN = r"^01[0125][0-9]{8}$"
# A time like 09:00 or 18:00
TIME_PATTERN = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"
# A booking reference like NFC-3F9A1C
REFERENCE_PATTERN = r"^NFC-[0-9A-F]{6}$"


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(ge=1, examples=[1])
    day: Weekday = Field(examples=["thursday"])
    time: str = Field(pattern=TIME_PATTERN, examples=["18:00"])
    patient_name: str = Field(min_length=2, max_length=80, examples=["Ahmed Hassan"])
    phone: str = Field(pattern=PHONE_PATTERN, examples=["01012345678"])


class AppointmentOut(BaseModel):
    """What the patient gets back. The phone number is never sent back."""
    reference: str
    doctor_id: int
    doctor_name: str
    day: Weekday
    time: str
    patient_name: str
