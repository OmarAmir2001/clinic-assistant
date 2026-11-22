# app/api/routes/doctors.py
from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencies import BookingServiceDep
from app.api.schemas.doctors import DoctorOut, FreeSlotsOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.core.enums import Specialty, Weekday
from app.repositories.doctors import Doctor

router = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    responses={**INVALID_INPUT, 404: {"model": ErrorResponse, "description": "No doctor with this id"}},
)

DoctorId = Annotated[int, Path(ge=1, description="The doctor's id, from GET /doctors")]


def to_out(doctor: Doctor) -> DoctorOut:
    return DoctorOut(
        id=doctor.id,
        name=doctor.name,
        name_ar=doctor.name_ar,
        specialty=doctor.specialty,
        fee_egp=doctor.fee_egp,
        days=list(doctor.schedule),
    )


@router.get("")
def list_doctors(
    service: BookingServiceDep,
    specialty: Specialty | None = None,
    day: Weekday | None = None,
) -> list[DoctorOut]:
    """List the clinic's doctors. Filter by specialty, by working day, or both."""
    return [to_out(d) for d in service.list_doctors(specialty=specialty, day=day)]


@router.get("/{doctor_id}")
def get_doctor(doctor_id: DoctorId, service: BookingServiceDep) -> DoctorOut:
    """One doctor, by id."""
    return to_out(service.get_doctor(doctor_id))


@router.get("/{doctor_id}/slots")
def free_slots(doctor_id: DoctorId, day: Weekday, service: BookingServiceDep) -> FreeSlotsOut:
    """The times this doctor is still free on a given day."""
    return FreeSlotsOut(doctor_id=doctor_id, day=day, free_times=service.free_slots(doctor_id, day))
