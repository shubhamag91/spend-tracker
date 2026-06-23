import shutil
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.ingestion.pipeline import run_ingestion
from app.models.transaction import IngestLog
from app.models.account import Account
from app.schemas.transaction import IngestLogOut

router = APIRouter(tags=["ingestion"])

ALLOWED_EXTENSIONS = {".csv", ".pdf", ".xlsx", ".xls"}


@router.post("/upload", response_model=IngestLogOut, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Query("real", pattern="^(real|demo)$"),
    account_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: CSV, PDF, XLSX, XLS.")

    if account_id is not None and not db.query(Account).filter(Account.id == account_id).first():
        raise HTTPException(status_code=404, detail="Account not found")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        log = run_ingestion(tmp_path, db, data_mode=mode, account_id=account_id)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return log


@router.get("/ingest-log", response_model=list[IngestLogOut])
def list_ingest_log(db: Session = Depends(get_db)):
    return db.query(IngestLog).order_by(IngestLog.ingested_at.desc()).limit(100).all()


@router.get("/ingest-log/{log_id}", response_model=IngestLogOut)
def get_ingest_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(IngestLog).filter(IngestLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log
