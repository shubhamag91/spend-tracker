from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, String, DateTime
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
    keyword: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # "NETFLIX"
    type: Mapped[str] = mapped_column(String, nullable=False, default="Other")  # OTT / AI / …
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
