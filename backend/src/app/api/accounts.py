from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.account import AccountOut, AccountCreate, AccountUpdate, AccountStatus

router = APIRouter(prefix="/accounts", tags=["accounts"])

_VALID_TYPES = {"bank", "card"}


def _validate_type(t: str) -> None:
    if t not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"type must be one of {sorted(_VALID_TYPES)}")


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.type, Account.name).all()


@router.get("/status", response_model=list[AccountStatus])
def accounts_status(mode: str = Query("real", pattern="^(real|demo)$"), db: Session = Depends(get_db)):
    """Per-account freshness: the latest transaction date (how current the data is)
    and transaction count — so you can see which account needs a new statement."""
    rows = (
        db.query(Account, func.min(Transaction.date), func.max(Transaction.date), func.count(Transaction.id))
        .outerjoin(Transaction, and_(Transaction.account_id == Account.id, Transaction.data_mode == mode))
        .group_by(Account.id)
        .order_by(Account.type, Account.name)
        .all()
    )

    def _as_date(v):
        if isinstance(v, str):  # SQLite may return the date as text
            from datetime import datetime as _dt
            return _dt.strptime(v[:10], "%Y-%m-%d").date()
        return v

    out = []
    for acct, earliest, latest, count in rows:
        out.append(AccountStatus(
            id=acct.id, name=acct.name, type=acct.type, last4=acct.last4,
            earliest_transaction_date=_as_date(earliest), latest_transaction_date=_as_date(latest),
            transaction_count=count,
        ))
    return out


@router.post("", response_model=AccountOut, status_code=201)
def create_account(body: AccountCreate, db: Session = Depends(get_db)):
    _validate_type(body.type)
    if db.query(Account).filter(Account.name == body.name).first():
        raise HTTPException(status_code=409, detail="An account with that name already exists")
    acct = Account(name=body.name, type=body.type, issuer=body.issuer, last4=body.last4)
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, body: AccountUpdate, db: Session = Depends(get_db)):
    acct = db.query(Account).filter(Account.id == account_id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    if body.type is not None:
        _validate_type(body.type)
        acct.type = body.type
    if body.name is not None:
        acct.name = body.name
    if body.issuer is not None:
        acct.issuer = body.issuer
    if body.last4 is not None:
        acct.last4 = body.last4
    db.commit()
    db.refresh(acct)
    return acct


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acct = db.query(Account).filter(Account.id == account_id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    # transactions.account_id is ON DELETE SET NULL, so rows survive untagged
    db.delete(acct)
    db.commit()
