from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SubscriptionRule(Base):
    """A recognised subscription service — a keyword + the type it belongs to.

    A transaction whose description contains the keyword (case-insensitive) is a
    subscription of that type. Unlike investments, subscriptions are still real
    spend — this is a detection/reporting overlay, it does not change spend totals.
    `name` is the display label (e.g. "Netflix"); `keyword` is what's matched.
    """
    __tablename__ = "subscription_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)            # "Netflix"
    # NOT unique: one merchant string can host several bills, split by min_amount
    # (e.g. "Airtel Payments Bank" → parents' electricity ≥₹1,000 and the phone bill).
    keyword: Mapped[str] = mapped_column(String, nullable=False)         # "NETFLIX"
    type: Mapped[str] = mapped_column(String, nullable=False, default="Other")  # OTT / AI / …
    # Billing cadence, used to normalise each charge to a monthly cost:
    # monthly | quarterly | yearly | weekly | variable (irregular lump-sum).
    frequency: Mapped[str] = mapped_column(String, nullable=False, default="monthly")
    # Optional amount floor — only charges >= this count, to disambiguate a big
    # recurring bill from small payments that share the same merchant string
    # (e.g. a ₹5,200 electricity bill vs a ₹111 charge, both "Airtel Payments Bank").
    min_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Optional explicit monthly cost — overrides frequency-based normalisation.
    # Useful when you know the monthly rate better than the data (e.g. a lump-sum
    # prepaid maintenance recharge of ₹20,007 that really costs ₹5,200/month).
    monthly_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
