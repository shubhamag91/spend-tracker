"""Parser for Axis Bank credit-card statements (e.g. Airtel Axis Mastercard).

Transaction lines are `DD/MM/YYYY  <description> <category>  <amount>  <Dr|Cr>`:

    14/05/2026 AIRTEL PAYMENTS BANK L,GURGAON UTILITIES 111.13 Dr
    25/05/2026 BBPS PAYMENT RECEIVED - DP2161452VFFUHFSIG94 4,732.48 Cr

The trailing `Dr`/`Cr` is an explicit debit/credit marker.

Note: Axis statements are often password-protected. The ingestion layer decrypts
to a temporary unlocked copy before this parser sees the file, so `can_parse` /
`parse` operate on an already-readable PDF.
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List
import pdfplumber
from app.ingestion.base import BaseParser, RawTransaction

# DD/MM/YYYY  <description>  <amount>  <Dr|Cr>   (end of line)
_TXN_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"     # date
    r"(.+?)\s+"                    # description (incl. trailing category word)
    r"([\d,]+\.\d{2})\s+"         # amount
    r"(Dr|Cr)$"                    # Dr = debit, Cr = credit
)


class AxisCardParser(BaseParser):
    SOURCE_NAME = "axis_card"

    def can_parse(self, filepath: str, headers: List[str]) -> bool:
        if Path(filepath).suffix.lower() != ".pdf":
            return False
        try:
            with pdfplumber.open(filepath) as pdf:
                head = (pdf.pages[0].extract_text() or "").upper()
        except Exception:
            return False  # still encrypted / unreadable
        return "AXIS BANK" in head and "CREDIT CARD" in head

    def parse(self, filepath: str) -> List[RawTransaction]:
        rows: List[RawTransaction] = []
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        for line in text.split("\n"):
            m = _TXN_RE.match(line.strip())
            if not m:
                continue
            date_s, desc, amount_s, drcr = m.groups()
            try:
                txn_date = datetime.strptime(date_s, "%d/%m/%Y").date()
            except ValueError:
                continue
            amount = float(amount_s.replace(",", ""))
            if amount == 0:
                continue
            rows.append(RawTransaction(
                date=txn_date,
                amount=amount,
                transaction_type="debit" if drcr == "Dr" else "credit",
                description=re.sub(r"\s+", " ", desc).strip(),
                source=self.SOURCE_NAME,
            ))
        return rows
