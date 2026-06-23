from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SubscriptionRuleOut(BaseModel):
    id: int
    name: str
    keyword: str
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionRuleCreate(BaseModel):
    name: str
    keyword: str
    type: str = "Other"


class SubscriptionItem(BaseModel):
    name: str
    type: str
    amount: float        # most recent charge (a monthly-cost proxy)
    total: float         # sum over the window
    count: int
    last_date: Optional[str]


class TypeBreakdown(BaseModel):
    type: str
    total: float
    count: int


class SubscriptionSummary(BaseModel):
    total: float                       # sum of all subscription charges in the window
    monthly_estimate: float            # sum of each service's most-recent charge
    service_count: int
    by_type: List[TypeBreakdown]
    items: List[SubscriptionItem]
