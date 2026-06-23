"""Parser for SBI Card credit-card statements.

Transaction lines are `DD Mon YY  <description>  <amount>  <D|C>`, e.g.

    03 May 26 YOUTUBE DI SI MUMBAI IN 89.00 D
    03 May 26 CARD CASHBACK CREDIT 385.00 C
    14 May 26 PAYMENT RECEIVED 000DP216134Y78UQBHU1MBF 7,315.00 C

The trailing `D`/`C` is an explicit debit/credit marker, so direction is exact.
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List
import pdfplumber
from app.ingestion.base import BaseParser, RawTransaction

# DD Mon YY  <description>  <amount>  <D|C>   (end of line)
_TXN_RE = re.compile(
    r"^(\d{2}\s+[A-Za-z]{3}\s+\d{2})\s+"   # date: 03 May 26
    r"(.+?)\s+"                             # description
    r"([\d,]+\.\d{2})\s+"                   # amount
    r"([DC])$"                              # D = debit, C = credit
)


class SbiCardParser(BaseParser):
    SOURCE_NAME = "sbi_card"

    def can_parse(self, filepath: str, headers: List[str]) -> bool:
        if Path(filepath).suffix.lower() != ".pdf":
            return False
        try:
            with pdfplumber.open(filepath) as pdf:
                head = (pdf.pages[0].extract_text() or "").upper()
        except Exception:
            return False
        return "SBI CARD" in head

    def parse(self, filepath: str) -> List[RawTransaction]:
        rows: List[RawTransaction] = []
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        for line in text.split("\n"):
            m = _TXN_RE.match(line.strip())
            if not m:
                continue
            date_s, desc, amount_s, dc = m.groups()
            try:
                txn_date = datetime.strptime(date_s, "%d %b %y").date()
            except ValueError:
                continue
            amount = float(amount_s.replace(",", ""))
            if amount == 0:
                continue
            rows.append(RawTransaction(
                date=txn_date,
                amount=amount,
                transaction_type="debit" if dc == "D" else "credit",
                description=re.sub(r"\s+", " ", desc).strip(),
                source=self.SOURCE_NAME,
            ))
        return rows
