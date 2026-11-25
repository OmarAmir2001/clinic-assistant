# app/api/schemas/appointments.py
from datetime import date

from pydantic import BaseModel, Field

from app.core.enums import AppointmentStatus

# An Egyptian mobile number: 010, 011, 012 or 015, then 8 digits
PHONE_PATTERN = r"^01[0125][0-9]{8}$"
# A booking reference like NFC-3F9A1C
REFERENCE_PATTERN = r"^NFC-[0-9A-F]{6}$"
# The client's name for one booking attempt: 8 to 64 letters, digits or dashes (a UUID fits)
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9-]{8,64}$"


class AppointmentCreate(BaseModel):
    slot_id: int = Field(ge=1, examples=[1], description="From GET /doctors/{doctor_id}/slots")
    patient_name: str = Field(min_length=2, max_length=80, examples=["Ahmed Hassan"])
    phone: str = Field(pattern=PHONE_PATTERN, examples=["01012345678"])


class RescheduleRequest(BaseModel):
    slot_id: int = Field(ge=1, examples=[2], description="The new slot, from GET /doctors/{doctor_id}/slots")


class AppointmentOut(BaseModel):
    """What the patient gets back. The phone number is never sent back."""
    reference: str
    status: AppointmentStatus
    doctor_id: int
    doctor_name: str
    day: date
    time: str
    patient_name: str
