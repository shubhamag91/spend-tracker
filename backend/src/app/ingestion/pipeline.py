import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.ingestion.registry import get_parser
from app.ingestion.normalizer import normalize_and_insert
from app.models.transaction import IngestLog
from app.utils.dedup import file_hash as compute_file_hash
from app.utils.interbank import reconcile_internal_transfers
from app.utils.pdf_decrypt import unlock_if_encrypted
from app.utils.file_naming import rename_to_statement_date


def run_ingestion(
    filepath: str,
    db: Session,
    data_mode: str = "real",
    account_id: int | None = None,
    rename_on_success: bool = False,
) -> IngestLog:
    """Main entry point for ingesting a CSV or PDF file."""
    filename = Path(filepath).name
    fhash = compute_file_hash(filepath)

    # File-level dedup: skip if already successfully ingested
    existing_log = (
        db.query(IngestLog)
        .filter(IngestLog.file_hash == fhash, IngestLog.status == "success")
        .first()
    )
    if existing_log:
        return existing_log

    log = IngestLog(filename=filename, file_hash=fhash, parser_used="unknown", status="pending")
    db.add(log)
    db.commit()
    db.refresh(log)

    unlocked_path = None
    try:
        # Password-protected PDFs (e.g. Axis cards) → unlock to a temp copy first.
        unlocked_path = unlock_if_encrypted(filepath)
        parse_path = unlocked_path or filepath

        parser = get_parser(parse_path)
        log.parser_used = parser.SOURCE_NAME
        raw_txns = parser.parse(parse_path)
        log.rows_parsed = len(raw_txns)

        inserted, skipped = normalize_and_insert(raw_txns, db, fhash, data_mode, account_id)
        log.rows_inserted = inserted
        log.rows_skipped = skipped
        log.status = "success"
        # Re-pair cross-account transfers now that this file's rows are in.
        if inserted:
            reconcile_internal_transfers(db, data_mode)
        if rename_on_success:
            new_path = rename_to_statement_date(filepath, raw_txns)
            log.filename = Path(new_path).name
    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
    finally:
        if unlocked_path and os.path.exists(unlocked_path):
            os.unlink(unlocked_path)

    db.commit()
    db.refresh(log)
    return log
