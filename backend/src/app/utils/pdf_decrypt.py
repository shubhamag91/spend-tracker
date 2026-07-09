"""Transparently unlock password-protected PDF statements before parsing.

Statement PDFs from some issuers (e.g. Axis credit cards) are encrypted. Rather
than thread a password through every parser, we decrypt an encrypted PDF to a
temporary unlocked copy up front and hand that path to the parser. Passwords come
from settings.pdf_passwords (config/.env, gitignored) — each is tried in turn.
"""
from __future__ import annotations
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.config import settings


def unlock_if_encrypted(filepath: str) -> str | None:
    """If `filepath` is an encrypted PDF, write an unlocked copy to a temp file and
    return its path (caller must delete it). Returns None if no unlocking is needed.
    Raises ValueError if the PDF is encrypted but no configured password works.
    """
    if Path(filepath).suffix.lower() != ".pdf":
        return None

    reader = PdfReader(filepath)
    if not reader.is_encrypted:
        return None

    # Try an empty owner password first, then each configured user password.
    for pw in ["", *settings.pdf_passwords]:
        try:
            if reader.decrypt(pw):  # 0 = failure, 1/2 = success
                break
        except Exception:
            continue
    else:
        raise ValueError(
            "PDF is password-protected and no password in PDF_PASSWORDS unlocked it "
            "(set PDF_PASSWORDS in config/.env)."
        )

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="unlocked_")
    with open(fd, "wb") as f:
        writer.write(f)
    return tmp_path
