from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Integer, String, Float, Boolean, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CashExpense(Base):
    """A recurring cash expense (cook, maid, driver, gym…) that never lands on a bank
    or card statement. Each active expense auto-generates a real debit transaction per
    period on the "Cash" account, so it flows into overall spend and the Fixed Spends
    page automatically — no manual entry each month."""
    __tablename__ = "cash_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)                       # "House Cook"
    amount: Mapped[float] = mapped_column(Float, nullable=False)                    # 8000
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1)   # 1..28
    frequency: Mapped[str] = mapped_column(String, nullable=False, default="monthly")
    type: Mapped[str] = mapped_column(String, nullable=False, default="Cash")       # Fixed-Spends type (e.g. Staff)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)         # first period (else earliest data month)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
