# app/db/models.py
"""The clinic's seven tables, written as Python classes. SQLAlchemy turns each class into a table."""
import uuid
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Every table class inherits from Base, so SQLAlchemy knows all of them."""


# ===== Knowledge: the documents from Session 4, and their chunks =====

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("type IN ('pdf', 'txt', 'md')", name="document_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    stored_as: Mapped[str]  # our random file name on disk (Session 6)
    size_bytes: Mapped[int]  # (Session 6)
    sha256: Mapped[str] = mapped_column(unique=True)  # the same file can't be stored twice
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)  # the database numbers them: 1, 2, 3 ...
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    position: Mapped[int]  # 0, 1, 2 ... inside its document
    text: Mapped[str]
    page: Mapped[int | None]  # "| None": this column may be empty
    section: Mapped[str | None]
    looks_broken: Mapped[bool] = mapped_column(default=False)  # broken Arabic from a bad PDF (Session 6)


# ===== Booking: doctors, their time slots, and appointments =====

class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = (CheckConstraint("fee_egp > 0", name="positive_fee"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)  # the ids from doctors.json
    name: Mapped[str]
    name_ar: Mapped[str]
    specialty: Mapped[str]
    fee_egp: Mapped[int]


class TimeSlot(Base):
    """One appointment time a doctor offers, on a real date."""

    __tablename__ = "time_slots"
    __table_args__ = (UniqueConstraint("doctor_id", "day", "start_time"),)  # the same slot can't exist twice

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    day: Mapped[date]
    start_time: Mapped[time]

    doctor: Mapped[Doctor] = relationship()  # slot.doctor: the Doctor row this slot points at (Session 6)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("status IN ('booked', 'cancelled')", name="appointment_status"),
        # At most ONE booked appointment per slot. Cancelled ones don't count.
        Index("one_booking_per_slot", "slot_id", unique=True,
              sqlite_where=text("status = 'booked'"), postgresql_where=text("status = 'booked'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(unique=True)  # what the patient sees, like NFC-3F9A1C
    slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    patient_name: Mapped[str]
    phone: Mapped[str]
    status: Mapped[str] = mapped_column(default="booked")
    idempotency_key: Mapped[str | None] = mapped_column(unique=True)  # one booking per request key (Session 6)

    slot: Mapped[TimeSlot] = relationship()  # appointment.slot, then appointment.slot.doctor (Session 6)


# ===== Chat: conversations and their messages =====

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant')", name="message_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str]
    content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
