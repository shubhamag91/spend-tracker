from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class InvestmentRule(Base):
    """A user-defined keyword that marks matching transactions as investments.

    Matched case-insensitively as a substring of the description (e.g. "LENDBOX",
    "INDIAN CLEARING"). Supplements the built-in `investment_keywords` from config
    so the user can teach the app about platforms it didn't ship knowing.
    """
    __tablename__ = "investment_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # Optional display name for the by-platform breakdown, when the description's
    # keyword isn't the real platform (e.g. keyword "INGENICO" → label "Grip",
    # because Grip routes its payments through the Ingenico gateway).
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
