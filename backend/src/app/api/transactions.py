from __future__ import annotations
import math
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionOut, TransactionPage
from app.utils.interbank import reconcile_internal_transfers

router = APIRouter(prefix="/transactions", tags=["transactions"])


# Whitelist of sortable columns → ORM attribute. Guards against arbitrary order_by.
_SORTABLE = {
    "date": Transaction.date,
    "amount": Transaction.amount,
}


@router.get("", response_model=TransactionPage)
def list_transactions(
    mode: str = Query("real", pattern="^(real|demo)$"),
    account_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    is_investment: Optional[bool] = None,
    sort_by: str = Query("date", pattern="^(date|amount)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.data_mode == mode)
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    if transaction_type:
        q = q.filter(Transaction.transaction_type == transaction_type)
    if is_investment is not None:
        q = q.filter(Transaction.is_investment == is_investment)

    total = q.count()
    sort_col = _SORTABLE[sort_by]
    primary = sort_col.asc() if sort_dir == "asc" else sort_col.desc()
    # id as a stable tiebreaker so equal values (esp. equal amounts) page deterministically
    items = (
        q.order_by(primary, Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TransactionPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("/reconcile-transfers")
def reconcile_transfers(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    """(Re)detect transfers between the user's own accounts and flag both sides
    as internal transfers. Returns the matched pairs."""
    pairs = reconcile_internal_transfers(db, mode)
    return {
        "matched_pairs": len(pairs),
        "total_amount": round(sum(p.debit.amount for p in pairs), 2),
        "transfers": [
            {
                "amount": p.debit.amount,
                "from_account": p.debit.account.name if p.debit.account else None,
                "to_account": p.credit.account.name if p.credit.account else None,
                "debit_date": p.debit.date.isoformat(),
                "credit_date": p.credit.date.isoformat(),
                "debit_id": p.debit.id,
                "credit_id": p.credit.id,
            }
            for p in pairs
        ],
    }


@router.patch("/{txn_id}/investment", response_model=TransactionOut)
def set_investment(txn_id: int, is_investment: bool = Query(...), db: Session = Depends(get_db)):
    """Manually mark/unmark a transaction as an investment (moves it Spent ↔ Invested)."""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.is_investment = is_investment
    db.commit()
    db.refresh(txn)
    return txn


@router.patch("/{txn_id}/category", response_model=TransactionOut)
def update_category(txn_id: int, category_id: Optional[int] = None, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.category_id = category_id
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
