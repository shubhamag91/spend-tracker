import hashlib
from pathlib import Path


def file_hash(filepath: str) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def row_hash(date: str, amount: float, description: str, account_id: int | None = None) -> str:
    """Stable per-row fingerprint for dedup.

    account_id is part of the payload so that an identical-looking transaction
    (same date, amount, description) appearing in two different accounts — e.g. a
    ₹200 Swiggy charge on both your HDFC and Yes Bank — is NOT collapsed into one.
    """
    payload = f"{account_id}|{date}|{amount:.2f}|{description.strip().lower()}"
    return hashlib.sha256(payload.encode()).hexdigest()
