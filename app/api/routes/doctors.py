# app/api/routes/doctors.py
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import BookingServiceDep
from app.api.schemas.doctors import DoctorOut, FreeSlotsOut, SlotOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.core.enums import Specialty
from app.db.models import Doctor

router = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    responses={**INVALID_INPUT, 404: {"model": ErrorResponse, "description": "No doctor with this id"}},
)

DoctorId = Annotated[int, Path(ge=1, description="The doctor's id, from GET /doctors")]
Day = Annotated[date, Query(description="A date, like 2026-12-08", examples=["2026-12-08"])]


def to_out(doctor: Doctor) -> DoctorOut:
    return DoctorOut(
        id=doctor.id, name=doctor.name, name_ar=doctor.name_ar, specialty=doctor.specialty, fee_egp=doctor.fee_egp
    )


@router.get("")
async def list_doctors(
    service: BookingServiceDep,
    specialty: Specialty | None = None,
    free_on: Annotated[date | None, Query(description="Only doctors with a free slot on this date")] = None,
) -> list[DoctorOut]:
    """List the clinic's doctors. Filter by specialty, by a date they have free slots, or both."""
    return [to_out(d) for d in await service.list_doctors(specialty=specialty, free_on=free_on)]


@router.get("/{doctor_id}")
async def get_doctor(doctor_id: DoctorId, service: BookingServiceDep) -> DoctorOut:
    """One doctor, by id."""
    return to_out(await service.get_doctor(doctor_id))


@router.get("/{doctor_id}/slots")
async def free_slots(doctor_id: DoctorId, day: Day, service: BookingServiceDep) -> FreeSlotsOut:
    """The slots this doctor still has free on a given date. Book one with its slot_id."""
    slots = await service.free_slots(doctor_id, day)
    return FreeSlotsOut(
        doctor_id=doctor_id,
        day=day,
        slots=[SlotOut(slot_id=s.id, time=s.start_time.strftime("%H:%M")) for s in slots],
    )
