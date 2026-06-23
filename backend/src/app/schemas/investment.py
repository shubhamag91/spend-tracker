from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class InvestmentRuleOut(BaseModel):
    id: int
    keyword: str
    label: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestmentRuleCreate(BaseModel):
    keyword: str
    label: Optional[str] = None


class PlatformInvest(BaseModel):
    name: str
    total: float
    count: int
    keyword: Optional[str] = None   # description substring to filter this platform's transactions


class InvestmentSummary(BaseModel):
    total_invested: float
    count: int
    by_platform: List[PlatformInvest]
