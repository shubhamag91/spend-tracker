from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SubscriptionRuleOut(BaseModel):
    id: int
    name: str
    keyword: str
    type: str
    frequency: str
    min_amount: Optional[float] = None
    monthly_amount: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionRuleCreate(BaseModel):
    name: str
    keyword: str
    type: str = "Other"
    frequency: str = "monthly"
    min_amount: Optional[float] = None
    monthly_amount: Optional[float] = None


class SubscriptionRuleUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None
    min_amount: Optional[float] = None
    monthly_amount: Optional[float] = None


class SubscriptionItem(BaseModel):
    name: str
    type: str
    frequency: str
    monthly: float       # charge normalised to a monthly cost
    amount: float        # most recent actual charge
    total: float         # sum over the window
    count: int
    last_date: Optional[str]


class TypeBreakdown(BaseModel):
    type: str
    monthly: float       # monthly-normalised total for the type
    count: int


class SubscriptionSummary(BaseModel):
    monthly_total: float               # sum of every item's monthly cost
    window_total: float                # raw sum of charges seen in the window
    service_count: int
    by_type: List[TypeBreakdown]
    items: List[SubscriptionItem]
