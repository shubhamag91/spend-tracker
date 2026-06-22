from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Account(Base):
    """A money source the user owns — a bank account or a credit card.

    Every transaction belongs to exactly one account. This is what lets the
    dashboard tell a Yes Bank debit from an HDFC debit, and a real card charge
    from the bank bill-payment that settles it.
    """
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # e.g. "HDFC Savings"
    type: Mapped[str] = mapped_column(String, nullable=False, default="bank")  # "bank" | "card"
    issuer: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. "HDFC", "Amex"
    last4: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # last 4 of acct/card no.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[List] = relationship("Transaction", back_populates="account")
