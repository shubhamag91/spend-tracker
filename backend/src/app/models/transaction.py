from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False, default="debit")
    description: Mapped[str] = mapped_column(String, nullable=False)
    raw_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    data_mode: Mapped[str] = mapped_column(String, nullable=False, default="real")
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_investment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_card_payment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # optional named bucket (e.g. "poker") — money that's neither spend nor income;
    # bucketed rows also carry is_internal_transfer=True so every spend/income query excludes them.
    bucket: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    row_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped[Optional[Category]] = relationship("Category", back_populates="transactions")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_date_mode", "date", "data_mode"),
        Index("idx_transactions_category", "category_id"),
        Index("idx_transactions_account", "account_id"),
    )


class IngestLog(Base):
    __tablename__ = "ingest_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False)
    parser_used: Mapped[str] = mapped_column(String, nullable=False)
    rows_parsed: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
