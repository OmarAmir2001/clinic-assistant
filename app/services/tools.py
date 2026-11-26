# app/services/tools.py
"""The agent's six tools: a form for each one's arguments, and the code that runs it."""
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.appointments import PHONE_PATTERN, REFERENCE_PATTERN
from app.core.config import Settings
from app.core.enums import ChangeAction, Specialty, ToolName, Weekday
from app.core.errors import AppError
from app.db.models import Doctor, TimeSlot
from app.providers.llm.openai_compatible import ToolCall
from app.services.answer import source_label
from app.services.booking import BookingService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

TIME_PATTERN = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"  # 24-hour time, like 18:00
DAY = "A weekday in English, like monday (means the next one); or a date YYYY-MM-DD only if the patient gave a date"


# ===== The contracts: one form per tool. The docstring and the descriptions are what the model reads =====

class SearchClinicDocs(BaseModel):
    """Search the clinic's documents: prices, insurance, opening hours, address, policies, how to prepare for tests."""
    question: str = Field(min_length=2, max_length=300, description="What to look for, in the patient's words")


class ListDoctors(BaseModel):
    """List all the clinic's doctors: name, specialty and fee in EGP."""


class CheckAvailability(BaseModel):
    """The free times of one doctor on one day."""
    doctor: str = Field(min_length=2, max_length=80, description="The doctor's name, or a specialty like dermatology")
    day: Weekday | date = Field(description=DAY)


class BookAppointment(BaseModel):
    """Book a free time for the patient. The patient is asked to confirm before anything is booked."""
    doctor: str = Field(min_length=2, max_length=80, description="The doctor's name, or a specialty like dermatology")
    day: Weekday | date = Field(description=DAY)
    time: str = Field(pattern=TIME_PATTERN, description="One of the free times from check_availability, like 18:00")
    patient_name: str = Field(min_length=2, max_length=80, description="The patient's full name")
    phone: str = Field(pattern=PHONE_PATTERN, description="Egyptian mobile number, 11 digits, like 01012345678")


class GetAppointment(BaseModel):
    """Look up an existing appointment by its reference and the phone number that booked it."""
    reference: str = Field(pattern=REFERENCE_PATTERN, description="Like NFC-3F9A1C")
    phone: str = Field(pattern=PHONE_PATTERN, description="The phone number used to book")


class CancelOrReschedule(BaseModel):
    """Cancel an appointment, or move it to another free time with the same doctor. The patient confirms first."""
    reference: str = Field(pattern=REFERENCE_PATTERN, description="Like NFC-3F9A1C")
    phone: str = Field(pattern=PHONE_PATTERN, description="The phone number used to book")
    action: ChangeAction = Field(description="cancel, or reschedule")
    new_day: Weekday | date | None = Field(default=None, description="For reschedule only. " + DAY)
    new_time: str | None = Field(default=None, pattern=TIME_PATTERN, description="For reschedule: like 18:00")


def without_refs(schema: dict) -> dict:
    """Put each shared definition ("$defs") where it is used ("$ref"). Not every server follows references."""
    definitions = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:  # {"$ref": "#/$defs/Weekday"} -> the Weekday definition itself
                return resolve(definitions[node["$ref"].split("/")[-1]])
            return {key: resolve(value) for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


@dataclass(frozen=True)
class Tool:
    """One thing the model may ask for: its name, the form for its arguments, and whether it changes anything."""
    name: ToolName
    form: type[BaseModel]
    writes: bool = False  # True: it changes the schedule, so it runs only after the patient says yes

    def spec(self) -> dict:
        """The tool as the model sees it: a name, a description, and a JSON schema made from the form."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.form.__doc__,
                "parameters": without_refs(self.form.model_json_schema()),
            },
        }


TOOLS = {
    tool.name: tool
    for tool in [
        Tool(ToolName.SEARCH_CLINIC_DOCS, SearchClinicDocs),
        Tool(ToolName.LIST_DOCTORS, ListDoctors),
        Tool(ToolName.CHECK_AVAILABILITY, CheckAvailability),
        Tool(ToolName.BOOK_APPOINTMENT, BookAppointment, writes=True),
        Tool(ToolName.GET_APPOINTMENT, GetAppointment),
        Tool(ToolName.CANCEL_OR_RESCHEDULE, CancelOrReschedule, writes=True),
    ]
}
SPECS = [tool.spec() for tool in TOOLS.values()]  # sent with every call to the model


# ===== Helpers: checking the model's arguments, and turning its words into our ids =====

class ToolError(AppError):
    """The model called a tool the wrong way. The message goes back to the model, so it can fix the call."""

    code = "tool_error"


PRIVATE = {"patient_name", "phone"}  # never in the log (constraint C-4)


def masked(arguments: str) -> str:
    """The arguments for the log, with the patient's name and phone hidden."""
    try:
        values = json.loads(arguments)
    except json.JSONDecodeError:
        return "(not JSON)"
    return json.dumps({k: "***" if k in PRIVATE else v for k, v in values.items()}, ensure_ascii=False)


def parse(call: ToolCall) -> BaseModel:
    """Check the model's arguments with the tool's form, like FastAPI checks a request body."""
    tool = TOOLS.get(call.name)
    if tool is None:
        raise ToolError(f"There is no tool called {call.name}. The tools are: {', '.join(TOOLS)}.")
    try:
        return tool.form.model_validate_json(call.arguments or "{}")
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(map(str, p['loc'])) or 'arguments'}: {p['msg']}" for p in error.errors())
        raise ToolError(f"Wrong arguments for {call.name}: {problems}") from error


def as_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)  # default=str: dates become "2026-12-03"


# The words patients use for each specialty, in English and Arabic: the model may pass any of them
SPECIALTY_WORDS = {
    Specialty.DERMATOLOGY: "dermatology dermatologist skin جلدية جلد",
    Specialty.PEDIATRICS: "pediatrics pediatrician children kids أطفال",
    Specialty.INTERNAL_MEDICINE: "internal-medicine internist باطنة باطنية",
    Specialty.DENTISTRY: "dentistry dentist teeth أسنان",
}
TITLES = {"doctor", "دكتور", "دكتورة"}


def matches(doctor: Doctor, text: str) -> bool:
    """Does the model's text name this doctor, or their specialty? ("Dr. Karim", "كريم", "dermatologist")"""
    known = f"{doctor.name} {doctor.name_ar} {SPECIALTY_WORDS[doctor.specialty]}".lower()
    words = [w for w in text.lower().replace(".", " ").split() if len(w) >= 3 and w not in TITLES]
    return any(w in known for w in words)  # one word is enough: "Mona", "أطفال"


def as_date(day: Weekday | date) -> date:
    """A weekday means the next one, today included: the model says "sunday", our code does the date math."""
    if isinstance(day, date):
        return day
    today = date.today()
    return next(today + timedelta(days=n) for n in range(7) if f"{today + timedelta(days=n):%A}".lower() == day)


def calendar(today: date, days: int = 14) -> str:
    """The next two weeks, written out. Small models are bad at date arithmetic: we do it for them."""
    return "\n".join(f"- {day:%A} {day.isoformat()}" for day in (today + timedelta(days=n) for n in range(days)))


WEEKDAYS_AR = {"Saturday": "السبت", "Sunday": "الأحد", "Monday": "الاثنين", "Tuesday": "الثلاثاء",
               "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة"}


def slot_text(doctor: Doctor, slot: TimeSlot, language: str = "en") -> str:
    """A slot as a person reads it: 'Dr. Mona Adel · Sunday 2026-11-29 · 18:00'."""
    name, weekday = doctor.name, f"{slot.day:%A}"
    if language == "ar":
        name, weekday = doctor.name_ar, WEEKDAYS_AR[weekday]
    return f"{name} · {weekday} {slot.day.isoformat()} · {slot.start_time:%H:%M}"


CONFIRM = {
    "en": 'Please confirm: {change}. Reply "yes" to go ahead, or tell me what to change.',
    "ar": 'من فضلك أكّد: {change}. اكتب "نعم" للمتابعة، أو أخبرني بما تريد تغييره.',
}
VERBS = {"en": {"book": "book", "cancel": "cancel", "move": "move"},
         "ar": {"book": "حجز", "cancel": "إلغاء", "move": "نقل"}}


# ===== The tools =====

class ClinicTools:
    """Runs the model's tool calls with our own services. Every result, good or bad, is JSON the model can read."""

    def __init__(self, session: AsyncSession, booking: BookingService, search: SearchService, settings: Settings):
        self.session = session  # the same session the booking and search services use
        self.booking = booking
        self.search = search
        self.settings = settings

    async def run(self, call: ToolCall) -> str:
        """Run one tool call. A mistake becomes {"error": ...} for the model to read, never a crash."""
        start = time.perf_counter()
        try:
            args = parse(call)
            result = await getattr(self, call.name)(args, call.id)
        except AppError as error:  # ToolError, NotFoundError, ConflictError
            result = {"error": error.message}
        finally:
            await self.end_reads()  # one tool call, one unit of work
        outcome = f"error: {result['error']}" if "error" in result else "ok"
        logger.info("Tool %s %s -> %s (%.2fs)", call.name, masked(call.arguments), outcome, time.perf_counter() - start)
        return as_json(result)

    async def end_reads(self) -> None:
        # A read starts a transaction and leaves it open. A booking must start its own (Session 6), so we end
        # the reads first. Without this: "A transaction is already begun on this Session"
        await self.session.commit()

    async def find_doctor(self, text: str) -> Doctor:
        doctors = await self.booking.list_doctors()
        found = [d for d in doctors if matches(d, text)]
        if len(found) != 1:
            names = "; ".join(f"{d.name} ({d.specialty})" for d in doctors)
            raise ToolError(f"No single doctor matches {text!r}. The doctors are: {names}.")
        return found[0]

    async def find_slot(self, doctor: Doctor, day: date, hhmm: str) -> TimeSlot:
        """The free slot at this time, or an error that says which times ARE free: the model can fix its call."""
        slots = await self.booking.free_slots(doctor.id, day)
        for slot in slots:
            if f"{slot.start_time:%H:%M}" == hhmm:
                return slot
        free = ", ".join(f"{s.start_time:%H:%M}" for s in slots) or "none"
        raise ToolError(f"{doctor.name} has no free slot at {hhmm} on {day:%A} {day}. Free times that day: {free}.")

    # Each tool gets its checked arguments and the call's id (book_appointment uses the id as its idempotency key)

    async def search_clinic_docs(self, args: SearchClinicDocs, call_id: str) -> dict:
        result = await self.search.search(args.question, self.settings.SEARCH_TOP_K)
        if not result.hits:
            return {"found": False, "message": "No clinic document answers this."}
        evidence = [{"source": source_label(hit.chunk), "text": hit.chunk.text} for hit in result.hits]
        return {"found": True, "evidence": evidence}

    async def list_doctors(self, args: ListDoctors, call_id: str) -> dict:
        doctors = await self.booking.list_doctors()
        return {"doctors": [
            {"name": d.name, "name_ar": d.name_ar, "specialty": d.specialty, "fee_egp": d.fee_egp} for d in doctors
        ]}

    async def check_availability(self, args: CheckAvailability, call_id: str) -> dict:
        doctor = await self.find_doctor(args.doctor)
        day = as_date(args.day)
        slots = await self.booking.free_slots(doctor.id, day)
        times = [f"{slot.start_time:%H:%M}" for slot in slots]
        # One value per field: the model copies what it sees, so "day" holds exactly what book_appointment accepts
        result = {"doctor": doctor.name, "day": day.isoformat(), "weekday": f"{day:%A}", "free_times": times}
        if not slots:
            result["message"] = "No free times on this day. Try another day."
        return result

    async def book_appointment(self, args: BookAppointment, call_id: str) -> dict:
        doctor = await self.find_doctor(args.doctor)
        slot = await self.find_slot(doctor, as_date(args.day), args.time)
        await self.end_reads()
        appointment = await self.booking.book(slot.id, args.patient_name, args.phone, idempotency_key=call_id)
        return {"booked": True, "reference": appointment.reference, "appointment": slot_text(doctor, slot)}

    async def get_appointment(self, args: GetAppointment, call_id: str) -> dict:
        appointment = await self.booking.get_appointment(args.reference, args.phone)
        slot = appointment.slot
        return {"reference": appointment.reference, "status": appointment.status,
                "appointment": slot_text(slot.doctor, slot), "patient_name": appointment.patient_name}

    async def cancel_or_reschedule(self, args: CancelOrReschedule, call_id: str) -> dict:
        if args.action == ChangeAction.CANCEL:
            await self.booking.cancel(args.reference, args.phone)
            return {"cancelled": True, "reference": args.reference}
        slot = await self.new_slot(args)
        await self.end_reads()
        appointment = await self.booking.reschedule(args.reference, args.phone, slot.id)
        return {"moved": True, "reference": appointment.reference,
                "appointment": slot_text(appointment.slot.doctor, appointment.slot)}

    async def new_slot(self, args: CancelOrReschedule) -> TimeSlot:
        appointment = await self.booking.get_appointment(args.reference, args.phone)
        if args.new_day is None or args.new_time is None:
            raise ToolError("To reschedule, give new_day and new_time (from check_availability).")
        return await self.find_slot(appointment.slot.doctor, as_date(args.new_day), args.new_time)

    # ===== Before a change: what exactly will happen, read from the database, not from the model's words =====

    async def preview(self, call: ToolCall, language: str) -> dict:
        """For book and cancel_or_reschedule: the change in the patient's language, and the exact arguments."""
        verb = VERBS[language]
        try:
            args = parse(call)
            if call.name == ToolName.BOOK_APPOINTMENT:
                doctor = await self.find_doctor(args.doctor)
                slot = await self.find_slot(doctor, as_date(args.day), args.time)
                change = f"{verb['book']} {slot_text(doctor, slot, language)} · {args.patient_name} · {args.phone}"
                exact = args.model_copy(update={"day": slot.day})  # "sunday" becomes the date we showed
            elif args.action == ChangeAction.CANCEL:
                slot = (await self.booking.get_appointment(args.reference, args.phone)).slot
                change = f"{verb['cancel']} {args.reference} ({slot_text(slot.doctor, slot, language)})"
                exact = args
            else:
                appointment = await self.booking.get_appointment(args.reference, args.phone)
                slot = await self.new_slot(args)
                doctor = appointment.slot.doctor  # a move keeps the same doctor
                old, new = slot_text(doctor, appointment.slot, language), slot_text(doctor, slot, language)
                change = f"{verb['move']} {args.reference}: {old} → {new}"
                exact = args.model_copy(update={"new_day": slot.day})
        except AppError as error:
            logger.info("Tool %s %s -> error: %s", call.name, masked(call.arguments), error.message)
            return {"error": error.message}
        finally:
            await self.end_reads()
        logger.info("Tool %s %s -> waiting for the patient's yes", call.name, masked(call.arguments))
        return {"confirm": CONFIRM[language].format(change=change), "arguments": exact.model_dump_json()}
