from sqlalchemy.orm import Session
from app.ingestion.base import RawTransaction
from app.models.transaction import Transaction, IngestLog
from app.categorization.engine import categorize
from app.utils.dedup import row_hash as compute_row_hash
from app.utils.transfers import is_internal_transfer
from app.utils.investments import is_investment
from app.utils.card_payments import is_card_payment

# Parser SOURCE_NAMEs that come from a credit-card statement (not a bank account).
_CARD_SOURCES = {"hdfc_card", "sbi_card", "axis_card", "amex_card"}


def normalize_and_insert(
    raw_txns: list[RawTransaction],
    db: Session,
    file_hash: str,
    data_mode: str = "real",
    account_id: int | None = None,
) -> tuple[int, int]:
    """Insert normalized transactions. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0
    # Count identical rows seen so far in THIS file. A statement can legitimately
    # list the same charge twice (e.g. two ₹2 or four ₹2,000 charges in one day);
    # the Nth repeat gets an occurrence suffix so it survives instead of colliding
    # on the UNIQUE row_hash. Re-importing the same file reproduces the same
    # suffixes, so cross-file dedup still works.
    batch_seq: dict[str, int] = {}

    for raw in raw_txns:
        base = compute_row_hash(str(raw.date), raw.amount, raw.description, account_id)
        seq = batch_seq.get(base, 0)
        batch_seq[base] = seq + 1
        rh = base if seq == 0 else f"{base}:{seq}"

        # Cross-file duplicate guard
        if db.query(Transaction).filter(Transaction.row_hash == rh).first():
            skipped += 1
            continue

        category_id = categorize(raw.description, db)
        internal = is_internal_transfer(raw.description)
        # investments flow both ways: SIP purchases (debit) and redemptions (credit)
        investment = is_investment(raw.description)
        # Card-bill settlements aren't consumption or income. Two cases:
        #  - a debit on a *bank* account paying a card (CRED CLUB, …)
        #  - any credit on a *card* statement (payment received, cashback, refund) —
        #    these settle the card, they are not real income.
        is_card_source = raw.source in _CARD_SOURCES
        card_payment = (
            (raw.transaction_type == "debit" and is_card_payment(raw.description))
            or (is_card_source and raw.transaction_type == "credit")
        )

        txn = Transaction(
            date=raw.date,
            amount=raw.amount,
            transaction_type=raw.transaction_type,
            description=raw.description.strip(),
            raw_description=raw.description,
            category_id=category_id,
            account_id=account_id,
            source=raw.source,
            data_mode=data_mode,
            is_internal_transfer=internal,
            is_investment=investment,
            is_card_payment=card_payment,
            file_hash=file_hash,
            row_hash=rh,
        )
        db.add(txn)
        inserted += 1

    db.commit()
    return inserted, skipped
