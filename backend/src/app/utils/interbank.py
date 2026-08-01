"""Detect transfers between the user's own tracked accounts.

A move between two accounts you own (e.g. HDFC → Yes Bank) shows up twice: a
*debit* in the source account and a *credit* of the same amount in the
destination account, a day or two apart. Neither is real consumption or real
income, so both sides are marked `is_internal_transfer=True` and drop out of
spend/income analytics.

Pairing is the stronger signal, but it only sees transfers where both statements
are loaded. So it layers on top of the narration check in `utils.transfers`:
that verdict is the baseline, and a confirmed pair upgrades a transaction to a
transfer even when the narration alone wouldn't have said so.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import Account
from app.utils.transfers import is_internal_transfer

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
    # Manual overrides carry a `bucket` (poker, a marked transfer, …). Leave those
    # alone — reconcile only manages auto-detected own-account pairs, so a re-import
    # never clobbers something the user tagged by hand.
    auto = [t for t in txns if t.bucket is None]
    # Reset to the narration-level verdict rather than to False. Pairing can only
    # see transfers where *both* statements are loaded, so a move into an account
    # whose statements start later (or aren't tracked at all) has no counterpart row
    # to match and would otherwise be reset to spend on every re-import.
    for t in auto:
        t.is_internal_transfer = is_internal_transfer(t.description)

    debits = sorted(
        (t for t in auto if t.transaction_type == "debit"),
        key=lambda t: (t.date, t.id),
    )
    credits = [t for t in auto if t.transaction_type == "credit"]
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
