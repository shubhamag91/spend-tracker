from __future__ import annotations
import csv
from pathlib import Path
from typing import List
from app.ingestion.base import BaseParser
from app.ingestion.csv_parsers.hdfc import HdfcCsvParser
from app.ingestion.csv_parsers.icici import IciciCsvParser
from app.ingestion.csv_parsers.generic import GenericCsvParser
from app.ingestion.pdf_parsers.statement import PdfStatementParser
from app.ingestion.pdf_parsers.hdfc_card import HdfcCardParser
from app.ingestion.pdf_parsers.sbi_card import SbiCardParser
from app.ingestion.pdf_parsers.axis_card import AxisCardParser
from app.ingestion.pdf_parsers.amex_card import AmexCardParser
from app.ingestion.xlsx_parser import XlsxParser

_PARSERS: List[BaseParser] = [
    HdfcCsvParser(),
    IciciCsvParser(),
    # specific credit-card layouts — must precede the generic PDF parser
    HdfcCardParser(),
    SbiCardParser(),
    AxisCardParser(),
    AmexCardParser(),
    PdfStatementParser(),
    XlsxParser(),
    GenericCsvParser(),
]


def _read_csv_headers(filepath: str) -> List[str]:
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    return [col.strip() for col in row]
    except Exception:
        pass
    return []


def get_parser(filepath: str) -> BaseParser:
    ext = Path(filepath).suffix.lower()
    headers = _read_csv_headers(filepath) if ext == ".csv" else []
    for parser in _PARSERS:
        if parser.can_parse(filepath, headers):
            return parser
    return GenericCsvParser()
