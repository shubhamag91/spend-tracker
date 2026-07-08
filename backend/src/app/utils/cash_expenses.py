"""Generate the recurring debits for cash expenses (cook, maid, …).

Cash expenses never hit a statement, so we materialise them as real transactions on
a synthetic "Cash" account. One debit per period from the expense's start up to today,
idempotent (row_hash dedup) — so running this on every startup just fills the months
that have elapsed since last time.
"""
from __future__ import annotations
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.cash_expense import CashExpense
from app.utils.dedup import row_hash

CASH_SOURCE = "cash_expense"


def cash_account(db: Session) -> Account:
    acct = db.query(Account).filter(Account.name == "Cash").first()
    if not acct:
        acct = Account(name="Cash", type="cash")
        db.add(acct)
        db.commit()
        db.refresh(acct)
    return acct


def _months(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def sync_cash_expenses(db: Session, mode: str = "real") -> int:
    """Materialise every active cash expense up to today. Returns rows inserted."""
    expenses = db.query(CashExpense).filter(CashExpense.active == True).all()  # noqa: E712
    if not expenses:
        return 0

    # generate at least through the data window, and through real 'today' if it's later
    earliest = db.query(func.min(Transaction.date)).filter(Transaction.data_mode == mode).scalar()
    latest = db.query(func.max(Transaction.date)).filter(Transaction.data_mode == mode).scalar()
    end = max([d for d in (date.today(), latest) if d] or [date.today()])
    cash = cash_account(db)

    inserted = 0
    for e in expenses:
        if e.frequency != "monthly":
            continue  # only monthly supported for now
        start = e.start_date or (earliest.replace(day=1) if earliest else end.replace(day=1))
        day = min(max(e.day_of_month, 1), 28)
        for y, m in _months(start.replace(day=1), end):
            d = date(y, m, day)
            if d < start or d > end:
                continue
            rh = row_hash(str(d), e.amount, e.name, cash.id)
            if db.query(Transaction).filter(Transaction.row_hash == rh).first():
                continue
            db.add(Transaction(
                date=d, amount=e.amount, transaction_type="debit",
                description=e.name, raw_description=e.name, source=CASH_SOURCE,
                data_mode=mode, account_id=cash.id, row_hash=rh,
            ))
            inserted += 1
    db.commit()
    return inserted
