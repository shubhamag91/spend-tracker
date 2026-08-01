"""Detect internal / self transfers — money moved between the account holder's
own accounts. These are not real income or spend and must be excluded from
analytics, otherwise they inflate income and savings figures.

Heuristic: bank narrations put the *counterparty* in the field immediately after
the transfer reference (an IFSC code, or an IMPS reference number). When that
counterparty is the account holder, the money is going to / coming from another
account they own.

Position is what carries the meaning — the holder's name appearing *somewhere*
is not enough, because they are also the named beneficiary on every payment they
receive:

    NEFT DR-YESB0000524-YOURNAME-NETBANK, MUM-…        self transfer  (counterparty)
    NEFT CR-BARC0INBBIR-EXAMPLE CORP-YOURNAME-…        salary         (beneficiary)
    RTGS CR-SCBL0036001-SOME MUTUAL FUND-YOURNAME-…    redemption     (beneficiary)

A name-anywhere match flags all three, which silently wipes out real income. Only
the first has the holder in the counterparty slot.
"""
from __future__ import annotations
import re
from app.config import settings

_TRANSFER_PREFIX = r"(?:IMPS|NEFT|IFT|FT|MMT|RTGS|TPT|ACH)"
_IFSC = r"[A-Z]{4}[A-Z0-9]{7}"   # bank branch code, e.g. YESB0000524
_REF = r"\d{6,}"                 # bare reference number, e.g. IMPS-604053934010-…

# <PREFIX> [DR|CR] - <IFSC|ref> - <COUNTERPARTY> - <rest…>
# The counterparty runs to the next hyphen; capturing it lets us test *which*
# field the holder's name landed in rather than merely whether it is present.
_COUNTERPARTY = re.compile(
    rf"{_TRANSFER_PREFIX}\s*(?:DR|CR)?\s*-\s*(?:{_IFSC}|{_REF})\s*-\s*([^-]+)",
    re.IGNORECASE,
)

# Banks disagree on field order. Yes Bank writes outbound transfers back-to-front
# relative to HDFC — its own reference first, then a *beneficiary nickname*, then
# the destination IFSC:
#     NET-NEFT-YESOB62010073043-SHUBHAMHDFC-HDFC0000011-self-HDFC BANK
# The counterparty slot holds a nickname rather than the holder's name, so the
# positional check above can't see it. But the bank has already labelled the
# transfer "self", which is a stronger signal than any name match.
_HAS_TRANSFER = re.compile(rf"\b{_TRANSFER_PREFIX}\b", re.IGNORECASE)
_SELF_FIELD = re.compile(r"[-\s]SELF(?=[-\s]|$)", re.IGNORECASE)


def _normalize(text: str) -> str:
    """Uppercase and strip to alphanumerics so hyphen/space variations don't matter."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def is_internal_transfer(description: str, names: list[str] | None = None) -> bool:
    """True if the transfer is between the holder's own accounts.

    Either the narration carries an explicit "self" field, or the counterparty is
    the holder themselves. Returns False for payments where the holder is merely the
    beneficiary (salary, fund redemptions, vendor payouts) — those name the holder
    too, but in a later field.
    """
    names = names if names is not None else settings.account_holder_names
    if not names:
        return False
    # The bank saying "self" outright beats inferring it from the counterparty name.
    if _HAS_TRANSFER.search(description or "") and _SELF_FIELD.search(description or ""):
        return True
    match = _COUNTERPARTY.search(description or "")
    if not match:
        return False
    counterparty = _normalize(match.group(1))
    if not counterparty:
        return False
    return any(_normalize(name) == counterparty for name in names if _normalize(name))
