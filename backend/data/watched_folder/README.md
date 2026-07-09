# Watched folder — one subfolder per source

Drop a statement into the subfolder named after the account it belongs to, and it's
auto-imported **and tagged to that account** (no need to pick the account on upload).

```
watched_folder/
├── HDFC Savings/          ← bank statements for HDFC Savings (…1934)
├── Yes Bank/              ← bank statements for Yes Bank (…1758)
├── SBI Card/              ← SBI Card statements (…0098)
├── HDFC Regalia Gold/     ← HDFC Regalia Gold card (…9826)
├── HDFC Swiggy/           ← HDFC Swiggy card (…9991)
├── Axis Airtel/           ← Axis Airtel card (…3761)
├── Amex Platinum Travel/  ← Amex statements (…2007)
├── _Grip/                 ← NOT imported — Grip reports (Bonds & SDIs holdings)
└── _Lendbox/              ← NOT imported — Lendbox reports (per-annum returns ledger)
```

Rules:
- **Subfolder name must match the account name exactly** (spaces are fine) for auto-tagging.
- A file dropped at the top level (not in a subfolder) is still imported, but **untagged**.
- Folders starting with `_` are **skipped** — use them for reports and files you don't want ingested.
- Re-importing the same file is safe: duplicates are detected by content hash and ignored.
- After a successful import, the file is **auto-renamed to its statement date**
  (e.g. `2026-06-12.pdf`) so the folder stays browsable at a glance. A same-day
  collision gets `(2)`, `(3)`, etc. appended.
- **Password-protected PDFs** (e.g. Axis cards) are auto-decrypted before parsing —
  add the password to `PDF_PASSWORDS` in `backend/config/.env` (gitignored) and it's
  tried automatically on every locked PDF, no manual unlocking needed.

To add a new account folder, use the exact account name shown on the Accounts list.
