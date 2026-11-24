# examples/first_model.py
"""The same doctors table with SQLAlchemy: a Python class instead of SQL strings.

    uv run python examples/first_model.py

echo=True prints every SQL statement SQLAlchemy writes for us. The database lives in memory again.
"""
import asyncio

from sqlalchemy import CheckConstraint, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """The parent of every table class."""


class Doctor(Base):
    """One class = one table. One object = one row."""

    __tablename__ = "doctors"
    __table_args__ = (CheckConstraint("fee_egp > 0", name="positive_fee"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    fee_egp: Mapped[int]


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", echo=True)  # an in-memory SQLite; print the SQL

    # 1. Create the table: SQLAlchemy writes the CREATE TABLE for us
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine)
    async with sessions() as session:
        # 2. Add rows: plain Python objects. commit() writes the INSERTs
        session.add(Doctor(id=1, name="Dr. Mona Adel", fee_egp=450))
        session.add(Doctor(id=2, name="Dr. Karim Hassan", fee_egp=400))
        await session.commit()

        # 3. Read them back: SQLAlchemy writes the SELECT and gives us objects
        for doctor in await session.scalars(select(Doctor)):
            print(doctor.name, doctor.fee_egp)  # names, not positions
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
