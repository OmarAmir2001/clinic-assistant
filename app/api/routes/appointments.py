# app/api/routes/appointments.py
from typing import Annotated

from fastapi import APIRouter, Header, Path, status

from app.api.dependencies import BookingServiceDep
from app.api.schemas.appointments import (
    IDEMPOTENCY_KEY_PATTERN,
    PHONE_PATTERN,
    REFERENCE_PATTERN,
    AppointmentCreate,
    AppointmentOut,
    RescheduleRequest,
)
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.db.models import Appointment

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    responses={**INVALID_INPUT, 404: {"model": ErrorResponse, "description": "No such slot or appointment"}},
)

Reference = Annotated[str, Path(pattern=REFERENCE_PATTERN, description="The booking reference, like NFC-3F9A1C")]
# The phone travels in a header, not in the URL: URLs end up in server logs (constraint C-4)
PatientPhone = Annotated[str, Header(alias="X-Patient-Phone", pattern=PHONE_PATTERN)]
# A new key for each booking attempt; the SAME key when retrying that attempt
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", pattern=IDEMPOTENCY_KEY_PATTERN, description="Send the same key when you retry"),
]
CONFLICT = {409: {"model": ErrorResponse, "description": "The slot is already booked"}}


def to_out(appointment: Appointment) -> AppointmentOut:
    return AppointmentOut(
        reference=appointment.reference,
        status=appointment.status,
        doctor_id=appointment.slot.doctor_id,
        doctor_name=appointment.slot.doctor.name,
        day=appointment.slot.day,
        time=appointment.slot.start_time.strftime("%H:%M"),
        patient_name=appointment.patient_name,
    )


@router.post("", status_code=status.HTTP_201_CREATED, responses=CONFLICT)
async def book_appointment(
    request: AppointmentCreate, key: IdempotencyKey, service: BookingServiceDep
) -> AppointmentOut:
    """Book a free slot. The patient has already confirmed the details.

    Retrying with the same Idempotency-Key gives back the same booking, never a second one.
    """
    appointment = await service.book(request.slot_id, request.patient_name, request.phone, key)
    return to_out(appointment)


@router.get("/{reference}")
async def get_appointment(reference: Reference, phone: PatientPhone, service: BookingServiceDep) -> AppointmentOut:
    """Look up a booking. Only the phone number that booked it can see it."""
    return to_out(await service.get_appointment(reference, phone))


@router.delete("/{reference}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(reference: Reference, phone: PatientPhone, service: BookingServiceDep) -> None:
    """Cancel a booking and free its slot. Cancelling twice is harmless."""
    await service.cancel(reference, phone)


@router.post("/{reference}/reschedule", responses=CONFLICT)
async def reschedule_appointment(
    reference: Reference, request: RescheduleRequest, phone: PatientPhone, service: BookingServiceDep
) -> AppointmentOut:
    """Move a booking to another free slot, in one step: you never lose the old slot without getting the new one."""
    return to_out(await service.reschedule(reference, phone, request.slot_id))
