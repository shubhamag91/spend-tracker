from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    issuer: Optional[str] = None
    last4: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountCreate(BaseModel):
    name: str
    type: str = "bank"  # "bank" | "card"
    issuer: Optional[str] = None
    last4: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    issuer: Optional[str] = None
    last4: Optional[str] = None


class AccountStatus(BaseModel):
    id: int
    name: str
    type: str
    last4: Optional[str] = None
    latest_transaction_date: Optional[date] = None   # how current the account's data is
    transaction_count: int
