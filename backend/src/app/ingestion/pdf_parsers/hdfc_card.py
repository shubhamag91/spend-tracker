"""Parser for HDFC Bank credit-card statements (Regalia, Swiggy, Millennia, …).

These differ from HDFC *bank* statements: transactions are one per line as

    24/05/2026| 16:53 EMI MAKE MY TRIP INDIA PVTLTGURGAON + 500 C 18,878.00 l
    16/05/2026| 22:15 PYU*Swiggy FoodBangalore C 223.00 l

i.e. `DD/MM/YYYY| HH:MM <merchant><city> [+ <reward pts>] C <amount> l`, where
`C` and `l` are column markers and the trailing `+ <n>` is reward points. The
amount column carries no reliable debit/credit indicator in the extracted text,
so charges are treated as debits and the few credits (cashback / refund /
reversal) are detected by keyword.
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import List
import pdfplumber
from app.ingestion.base import BaseParser, RawTransaction

# DD/MM/YYYY |HH:MM  <description>  [+ <pts>]  C  <amount>  [l]
_TXN_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s*\|\s*\d{2}:\d{2}\s+"   # date | time
    r"(.+?)\s+"                                      # description (non-greedy)
    r"(?:\+\s*\d+\s+)?"                              # optional reward points
    r"C\s+([\d,]+\.\d{2})\b"                         # 'C' marker + amount
)
# Lines that are credits to the card (money back), not charges.
_CREDIT_KEYWORDS = ("CASHBACK", "CASH BACK", "REFUND", "REVERSAL", "REVERSED",
                    "PAYMENT RECEIVED", "MEMBERSHIP REVERSAL")


class HdfcCardParser(BaseParser):
    SOURCE_NAME = "hdfc_card"

    def can_parse(self, filepath: str, headers: List[str]) -> bool:
        if Path(filepath).suffix.lower() != ".pdf":
            return False
        try:
            with pdfplumber.open(filepath) as pdf:
                head = (pdf.pages[0].extract_text() or "").upper()
        except Exception:
            return False  # locked / unreadable → let another parser try
        return "HDFC BANK CREDIT CARD" in head and "CREDIT CARD STATEMENT" in head

    def parse(self, filepath: str) -> List[RawTransaction]:
        rows: List[RawTransaction] = []
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        for line in text.split("\n"):
            m = _TXN_RE.match(line.strip())
            if not m:
                continue
            date_s, desc, amount_s = m.groups()
            try:
                txn_date = datetime.strptime(date_s, "%d/%m/%Y").date()
            except ValueError:
                continue
            desc = re.sub(r"\s+", " ", desc).strip().rstrip("+").strip()
            amount = float(amount_s.replace(",", ""))
            if amount == 0:
                continue
            up = desc.upper()
            ttype = "credit" if any(k in up for k in _CREDIT_KEYWORDS) else "debit"
            rows.append(RawTransaction(
                date=txn_date, amount=amount, transaction_type=ttype,
                description=desc, source=self.SOURCE_NAME,
            ))
        return rows
