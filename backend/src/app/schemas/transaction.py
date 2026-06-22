from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class CategoryRef(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}


class AccountRef(BaseModel):
    id: int
    name: str
    type: str

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: int
    date: date
    amount: float
    transaction_type: str
    description: str
    source: str
    data_mode: str
    is_internal_transfer: bool = False
    is_investment: bool = False
    is_card_payment: bool = False
    created_at: datetime
    category: Optional[CategoryRef] = None
    account: Optional[AccountRef] = None

    model_config = {"from_attributes": True}


class TransactionPage(BaseModel):
    items: List[TransactionOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class IngestLogOut(BaseModel):
    id: int
    filename: str
    file_hash: str
    parser_used: str
    rows_parsed: int
    rows_inserted: int
    rows_skipped: int
    status: str
    error_message: Optional[str]
    ingested_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    total_spend: float
    total_credits: float
    daily_average: float
    top_category: Optional[str]
    transaction_count: int


class InsightItem(BaseModel):
    type: str   # 'warning' | 'tip' | 'info' | 'positive'
    title: str
    body: str


class TimeSeriesPoint(BaseModel):
    label: str
    total: float


class CategorySpend(BaseModel):
    category: str
    color: str
    total: float
    percentage: float


class WeeklyVelocityPoint(BaseModel):
    week_label: str   # "Week 1", "Week 2" …
    total: float
    change_pct: Optional[float]  # % change vs prior week


class HeatmapCell(BaseModel):
    day: str          # "Monday" … "Sunday"
    week_num: int     # 1-4
    total: float


class MerchantSpend(BaseModel):
    name: str
    category: str
    total: float
    count: int
    avg_per_txn: float


class RecurringTransaction(BaseModel):
    name: str
    category: str
    amount: float
    frequency: str    # "monthly" | "weekly" | "quarterly"
    next_due: Optional[str]


class IncomeMonthPoint(BaseModel):
    month: str
    actual: float
    expected: float


class IncomeSource(BaseModel):
    name: str
    total: float
    percentage: float
    source_type: str  # "salary" | "freelance" | "interest" | "other"


class SavingsPoint(BaseModel):
    month: str
    saved: float
    rate: float


class WalletSummary(BaseModel):
    loaded: float        # real money in (credits, excl. self-transfers & investment redemptions)
    topups: float        # self-transfers in from your own accounts
    other_in: float      # loaded minus topups
    invested: float      # money moved to broking / MF / SIP platforms (debits)
    spent: float         # actual consumption (debits excl. investments, transfers, card bills)
    card_bills: float    # credit-card bill settlements (spend already happened on the card)
    unspent: float       # loaded − invested − spent − card_bills
    spend_txns: int      # number of real spend transactions
