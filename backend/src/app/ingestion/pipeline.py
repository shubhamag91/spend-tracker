from pathlib import Path
from sqlalchemy.orm import Session
from app.ingestion.registry import get_parser
from app.ingestion.normalizer import normalize_and_insert
from app.models.transaction import IngestLog
from app.utils.dedup import file_hash as compute_file_hash


def run_ingestion(
    filepath: str, db: Session, data_mode: str = "real", account_id: int | None = None
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

    try:
        parser = get_parser(filepath)
        log.parser_used = parser.SOURCE_NAME
        raw_txns = parser.parse(filepath)
        log.rows_parsed = len(raw_txns)

        inserted, skipped = normalize_and_insert(raw_txns, db, fhash, data_mode, account_id)
        log.rows_inserted = inserted
        log.rows_skipped = skipped
        log.status = "success"
    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)

    db.commit()
    db.refresh(log)
    return log
