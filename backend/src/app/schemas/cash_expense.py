from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel


class CashExpenseCreate(BaseModel):
    name: str
    amount: float
    day_of_month: int = 1
    type: str = "Cash"
    frequency: str = "monthly"
    start_date: Optional[date] = None


class CashExpenseOut(BaseModel):
    id: int
    name: str
    amount: float
    day_of_month: int
    type: str
    frequency: str
    active: bool
    start_date: Optional[date] = None

    class Config:
        from_attributes = True
