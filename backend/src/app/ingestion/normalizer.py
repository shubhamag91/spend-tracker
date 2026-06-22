from sqlalchemy.orm import Session
from app.ingestion.base import RawTransaction
from app.models.transaction import Transaction, IngestLog
from app.categorization.engine import categorize
from app.utils.dedup import row_hash as compute_row_hash
from app.utils.transfers import is_internal_transfer
from app.utils.investments import is_investment
from app.utils.card_payments import is_card_payment


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

    for raw in raw_txns:
        rh = compute_row_hash(str(raw.date), raw.amount, raw.description, account_id)

        # Check for existing row_hash to detect duplicate
        existing = db.query(Transaction).filter(Transaction.row_hash == rh).first()
        if existing:
            skipped += 1
            continue

        category_id = categorize(raw.description, db)
        internal = is_internal_transfer(raw.description)
        # investments flow both ways: SIP purchases (debit) and redemptions (credit)
        investment = is_investment(raw.description)
        # credit-card bill settlements (debits only)
        card_payment = raw.transaction_type == "debit" and is_card_payment(raw.description)

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
