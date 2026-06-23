from __future__ import annotations
from datetime import datetime
from typing import List
from pydantic import BaseModel


class InvestmentRuleOut(BaseModel):
    id: int
    keyword: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestmentRuleCreate(BaseModel):
    keyword: str


class PlatformInvest(BaseModel):
    name: str
    total: float
    count: int


class InvestmentSummary(BaseModel):
    total_invested: float
    count: int
    by_platform: List[PlatformInvest]
