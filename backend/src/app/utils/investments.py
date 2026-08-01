"""Detect investment outflows — money moved into broking / mutual-fund / SIP
platforms. On a spending wallet these are wealth, not consumption, so they must
be separated from the spend total (otherwise a single ₹84k Grip transfer looks
like a spending blowout).

Three signals:
1. A broking UPI handle — VPAs from broking platforms carry a ".BRK@" segment,
   e.g. GRIPBROKING.CF.BRK@VALIDHDFC, INDSTOCKS.ICCL1.BRK@VALIDHDFC
2. A known investment-platform name in the description.
3. An outward forex remittance funding an overseas broking account.
"""
from __future__ import annotations
import re
from app.config import settings

_BROKING_VPA = re.compile(r"\.BRK@", re.IGNORECASE)

# HDFC books retail forex outward remittances as "RFX <ref> USD<amt>@<rate>".
# These fund an overseas broking account, so they are wealth rather than spend.
# Note this claims *every* RFX line as investment — if a remittance is ever sent
# for something else (travel, fees), mark that one by hand; a manual bucket wins
# over keyword detection.
_FOREX_REMITTANCE = re.compile(r"^\s*RFX\s+\S+\s+[A-Z]{3}[\d.]+@", re.IGNORECASE)


def investment_keywords(db) -> list[str]:
    """Built-in keywords from config plus user-defined InvestmentRule keywords."""
    from app.models.investment_rule import InvestmentRule
    custom = [r.keyword for r in db.query(InvestmentRule).all()]
    return list(settings.investment_keywords) + custom


def is_investment(description: str, names: list[str] | None = None) -> bool:
    names = names if names is not None else settings.investment_keywords
    if not description:
        return False
    if _BROKING_VPA.search(description) or _FOREX_REMITTANCE.search(description):
        return True
    up = description.upper()
    return any(k.upper() in up for k in names)
