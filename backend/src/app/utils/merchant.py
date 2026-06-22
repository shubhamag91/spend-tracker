"""Reduce a noisy bank description to a stable merchant/payee key.

Indian bank statements wrap the payee in transaction-type prefixes, IFSC codes,
VPA handles, and per-transaction reference numbers, e.g.

    UPI-CRED CLUB-CRED.CLUB@AXISB-UTIB0000114-645902607640-PAYMENT ON CRED
    ACH D- INDIAN CLEARING CORP-P7173384X179
    NEFT DR-PUNB0296800-SUBHASH KUMAR SINGH-NETBANK, MUM-HDFCH00911191177-APR26

The same recurring payee carries a *different* reference each time, so grouping
on the raw string never collapses them. `normalize_merchant` strips the noise and
returns the payee name (the field right after the prefix / IFSC) so recurring
detection and merchant rollups actually group.
"""
from __future__ import annotations
import re

# IFSC code: 4 letters, a 0, then 6 alphanumerics (e.g. UTIB0000114, PUNB0296800).
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
# Transaction-type / direction tokens that lead a description.
_PREFIX_TOKENS = {
    "UPI", "NEFT", "NEFT DR", "NEFT CR", "IMPS", "RTGS", "ACH", "ACH D", "ACH C",
    "POS", "ATM", "EAW", "TPT", "MMT", "FT", "INB", "BIL", "DR", "CR", "D", "C",
}


# Trailing-note fragments that aren't payees (often truncated by column width).
_NOISE_PREFIXES = ("PAID", "PAYMENT", "PAYME", "PAYMEN", "NETBANK")


def _is_reference(token: str) -> bool:
    """A reference/code/note field rather than a human/merchant name."""
    if token.startswith(_NOISE_PREFIXES):  # "PAID VIA CRED", "PAYMENT ON CRED"…
        return True
    if "@" in token:                       # VPA handle (cred.club@axisb)
        return True
    if _IFSC.match(token):                  # bank IFSC
        return True
    if re.fullmatch(r"\d+", token):         # pure number
        return True
    if re.search(r"\d{4,}", token):         # contains a long digit run (ref no.)
        return True
    # a single word (no spaces) with digits and length >= 8 → machine code, e.g.
    # NBBQGL4AIADLD6MA, BHARATPE2T0G0Z1S5J13888
    if " " not in token and len(token) >= 8 and any(c.isdigit() for c in token):
        return True
    return False


def normalize_merchant(description: str) -> str:
    """Best-effort payee name from a raw bank description (uppercased)."""
    s = (description or "").replace("\n", " ").upper()
    s = re.sub(r"\s+", " ", s).strip()
    parts = [p.strip() for p in s.split("-") if p.strip()]
    if not parts:
        return s[:40] or "UNKNOWN"
    for p in parts:
        if p in _PREFIX_TOKENS:
            continue
        if _is_reference(p):
            continue
        return p[:40]
    # nothing clean found — fall back to the first non-prefix field, else the whole
    for p in parts:
        if p not in _PREFIX_TOKENS:
            return p[:40]
    return parts[0][:40]
