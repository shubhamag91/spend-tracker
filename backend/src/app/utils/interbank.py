"""Detect transfers between the user's own tracked accounts.

A move between two accounts you own (e.g. HDFC → Yes Bank) shows up twice: a
*debit* in the source account and a *credit* of the same amount in the
destination account, a day or two apart. Neither is real consumption or real
income, so both sides are marked `is_internal_transfer=True` and drop out of
spend/income analytics.

This is more precise than name-only detection: an incoming salary/vendor payment
where you're merely the beneficiary has **no matching debit** in another tracked
account, so it is correctly left as income instead of being mistaken for a
self-transfer.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import Account

_AMOUNT_EPS = 0.01          # paise-level tolerance for "same amount"
_DEFAULT_WINDOW_DAYS = 3    # NEFT/IMPS usually settle same-day or next-day


@dataclass
class TransferPair:
    debit: Transaction
    credit: Transaction


def reconcile_internal_transfers(
    db: Session, mode: str = "real", window_days: int = _DEFAULT_WINDOW_DAYS
) -> list[TransferPair]:
    """Recompute `is_internal_transfer` for account-tagged transactions in `mode`.

    Resets the flag, then sets it on each debit↔credit pair that matches across
    two different accounts (same amount, within `window_days`). Returns the
    matched pairs. Untagged transactions are left untouched.
    """
    # Only bank↔bank moves are transfers. Credit-card debits are merchant
    # charges (never a transfer source), and card settlement is handled by the
    # is_card_payment flag — so restrict matching to bank accounts to avoid a
    # card charge falsely pairing with a same-amount bank credit.
    bank_ids = [a.id for a in db.query(Account).filter(Account.type == "bank").all()]
    txns = (
        db.query(Transaction)
        .filter(Transaction.data_mode == mode, Transaction.account_id.in_(bank_ids))
        .all()
    )
    for t in txns:
        t.is_internal_transfer = False

    debits = sorted(
        (t for t in txns if t.transaction_type == "debit"),
        key=lambda t: (t.date, t.id),
    )
    credits = [t for t in txns if t.transaction_type == "credit"]
    used: set[int] = set()
    pairs: list[TransferPair] = []

    for d in debits:
        best: Transaction | None = None
        best_gap: int | None = None
        for c in credits:
            if c.id in used or c.account_id == d.account_id:
                continue
            if abs(c.amount - d.amount) > _AMOUNT_EPS:
                continue
            gap = abs((c.date - d.date).days)
            if gap > window_days:
                continue
            if best_gap is None or gap < best_gap:
                best, best_gap = c, gap
        if best is not None:
            used.add(best.id)
            d.is_internal_transfer = True
            best.is_internal_transfer = True
            pairs.append(TransferPair(debit=d, credit=best))

    db.commit()
    return pairs
