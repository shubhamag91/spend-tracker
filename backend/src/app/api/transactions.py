from __future__ import annotations
import math
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
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
    transaction_type: Optional[str] = Query(None, pattern="^(debit|credit)$"),
    kind: Optional[str] = Query(None, pattern="^(spend|income|investment|transfer|poker)$"),
    is_investment: Optional[bool] = None,
    investment_platform: Optional[str] = None,   # filter by platform label (matches any of its keywords)
    search: Optional[str] = None,
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
    if kind == "spend":       # real consumption: debits that aren't investments/transfers/card-bills
        q = q.filter(Transaction.transaction_type == "debit", Transaction.is_investment == False,
                     Transaction.is_internal_transfer == False, Transaction.is_card_payment == False)
    elif kind == "income":    # real income: credits, same exclusions
        q = q.filter(Transaction.transaction_type == "credit", Transaction.is_investment == False,
                     Transaction.is_internal_transfer == False, Transaction.is_card_payment == False)
    elif kind == "investment":
        q = q.filter(Transaction.is_investment == True)
    elif kind == "transfer":   # auto + manually-marked transfers, but not poker
        q = q.filter(Transaction.is_internal_transfer == True,
                     or_(Transaction.bucket.is_(None), Transaction.bucket == "transfer"))
    elif kind == "poker":
        q = q.filter(Transaction.bucket == "poker")
    if is_investment is not None:
        q = q.filter(Transaction.is_investment == is_investment)
    if investment_platform:
        # a platform label can span several keywords — match any of them so the list
        # agrees with the by-platform breakdown count (e.g. Grip = GRIPX + LoanX + …)
        from app.api.investments import platform_keywords
        kws = platform_keywords(db, investment_platform)
        needles = kws or [investment_platform]   # manually-tagged label has no keyword
        q = q.filter(or_(*[Transaction.description.ilike(f"%{kw}%") for kw in needles]))
    if search:
        q = q.filter(Transaction.description.ilike(f"%{search}%"))

    total = q.count()
    total_amount = q.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar()
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
        total_amount=round(float(total_amount), 2),
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


@router.patch("/{txn_id}/transfer", response_model=TransactionOut)
def set_transfer(txn_id: int, is_transfer: bool = Query(...), db: Session = Depends(get_db)):
    """Manually mark/unmark a transaction as a transfer (money moved, not spent/earned —
    e.g. a loan to a friend that gets repaid). Excludes it from Spend and Income."""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.is_internal_transfer = is_transfer
    # tag it as a manual override so reconcile (on the next import) won't reset it
    txn.bucket = "transfer" if is_transfer else None
    db.commit()
    db.refresh(txn)
    return txn


@router.patch("/{txn_id}/poker", response_model=TransactionOut)
def set_poker(txn_id: int, is_poker: bool = Query(...), db: Session = Depends(get_db)):
    """Manually mark/unmark a one-off transaction as a poker settlement — for a
    counterparty not worth adding to POKER_KEYWORDS. Excludes it from Spend and Income."""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.is_internal_transfer = is_poker
    # tag it as a manual override so reconcile (on the next import) won't reset it
    txn.bucket = "poker" if is_poker else None
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
