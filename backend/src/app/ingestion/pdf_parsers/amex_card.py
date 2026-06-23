"""Parser for American Express (India) credit-card statements.

Transaction lines are `<Month> <Day> <description> <amount>`, e.g.

    April 5 PAYU*Swiggy Limited Bangalore 637.00
    April 17 PAYMENT RECEIVED. THANK YOU 26,169.13
    April 2 INSTALLMENT PRINCIPAL AMOUNT 25,552.92

The year isn't on the line, so it's taken from the statement date. Amex prints no
per-line Dr/Cr marker, so payments/credits are detected by keyword.
"""
from __future__ import annotations
import re
from datetime import date, datetime
from pathlib import Path
from typing import List
import pdfplumber
from app.ingestion.base import BaseParser, RawTransaction

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
_MONTH_ALT = "|".join(_MONTHS)

# <Month> <day> <description> <amount> [Cr]
_TXN_RE = re.compile(
    rf"^({_MONTH_ALT})\s+(\d{{1,2}})\s+(.+?)\s+([\d,]+\.\d{{2}})\s*(Cr)?$",
    re.IGNORECASE,
)
_CREDIT_KEYWORDS = ("PAYMENT RECEIVED", "THANK YOU", "CASHBACK", "REFUND",
                    "CREDIT BALANCE", "REVERSAL")


class AmexCardParser(BaseParser):
    SOURCE_NAME = "amex_card"

    def can_parse(self, filepath: str, headers: List[str]) -> bool:
        if Path(filepath).suffix.lower() != ".pdf":
            return False
        try:
            with pdfplumber.open(filepath) as pdf:
                head = (pdf.pages[0].extract_text() or "").upper()
        except Exception:
            return False
        return "AMERICAN EXPRESS" in head

    def parse(self, filepath: str) -> List[RawTransaction]:
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)

        # Statement date (dd/mm/yyyy) gives the year/month to anchor bare "Month Day".
        m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
        stmt_year = int(m.group(3)) if m else date.today().year
        stmt_month = int(m.group(2)) if m else 12

        rows: List[RawTransaction] = []
        for line in text.split("\n"):
            tm = _TXN_RE.match(line.strip())
            if not tm:
                continue
            month_name, day_s, desc, amount_s, cr = tm.groups()
            month = _MONTHS[month_name.lower()]
            # a statement can straddle a year-end: a month later than the statement
            # month belongs to the previous year (e.g. Dec txns on a Jan statement)
            year = stmt_year - 1 if month > stmt_month else stmt_year
            try:
                txn_date = date(year, month, int(day_s))
            except ValueError:
                continue
            amount = float(amount_s.replace(",", ""))
            if amount == 0:
                continue
            up = desc.upper()
            is_credit = bool(cr) or any(k in up for k in _CREDIT_KEYWORDS)
            rows.append(RawTransaction(
                date=txn_date,
                amount=amount,
                transaction_type="credit" if is_credit else "debit",
                description=re.sub(r"\s+", " ", desc).strip(),
                source=self.SOURCE_NAME,
            ))
        return rows
