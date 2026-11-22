# app/api/routes/appointments.py
from typing import Annotated

from fastapi import APIRouter, Header, Path, status

from app.api.dependencies import BookingServiceDep
from app.api.schemas.appointments import PHONE_PATTERN, REFERENCE_PATTERN, AppointmentCreate, AppointmentOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.repositories.appointments import Appointment
from app.services.booking import BookingService

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    responses={**INVALID_INPUT, 404: {"model": ErrorResponse, "description": "No such doctor, slot or appointment"}},
)

Reference = Annotated[str, Path(pattern=REFERENCE_PATTERN, description="The booking reference, like NFC-3F9A1C")]
# The phone travels in a header, not in the URL: URLs end up in server logs (constraint C-4)
PatientPhone = Annotated[str, Header(alias="X-Patient-Phone", pattern=PHONE_PATTERN)]


def to_out(appointment: Appointment, service: BookingService) -> AppointmentOut:
    return AppointmentOut(
        reference=appointment.reference,
        doctor_id=appointment.doctor_id,
        doctor_name=service.get_doctor(appointment.doctor_id).name,
        day=appointment.day,
        time=appointment.time,
        patient_name=appointment.patient_name,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse, "description": "The slot is already booked"}},
)
def book_appointment(request: AppointmentCreate, service: BookingServiceDep) -> AppointmentOut:
    """Book a free slot. The patient has already confirmed the details."""
    appointment = service.book(
        doctor_id=request.doctor_id,
        day=request.day,
        time=request.time,
        patient_name=request.patient_name,
        phone=request.phone,
    )
    return to_out(appointment, service)


@router.get("/{reference}")
def get_appointment(reference: Reference, phone: PatientPhone, service: BookingServiceDep) -> AppointmentOut:
    """Look up a booking. Only the phone number that booked it can see it."""
    return to_out(service.get_appointment(reference, phone), service)


@router.delete("/{reference}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(reference: Reference, phone: PatientPhone, service: BookingServiceDep) -> None:
    """Cancel a booking and free its slot."""
    service.cancel(reference, phone)
