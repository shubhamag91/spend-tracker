# Spend Tracker

A full-stack personal finance dashboard that auto-ingests bank-statement exports
(CSV / PDF / XLS / XLSX), classifies every transaction, and visualizes your
spending across day, week, month, and year views. Built around a **wallet model**
— *loaded → invested → spent → unspent* — rather than the usual income/savings
framing, so "spent" means money you actually consumed. Includes a **demo mode**
toggle for sharing without exposing real finances.

> 📖 **Full documentation:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) is the
> single canonical reference — the mental model, every screen, the complete API,
> backend internals, the data model, and how each number is computed.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Frontend                                  │
│  React 19 + TypeScript + Vite + Tailwind + Recharts + TanStack Query │
│  Pages: Dashboard · Transactions · Income · Categories              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP (proxied via Vite dev server, /api)
┌──────────────────────────────▼──────────────────────────────────────┐
│                            Backend                                   │
│  FastAPI + SQLAlchemy + SQLite                                       │
│  ┌─────────────────────────┐   ┌──────────────────────────────────┐  │
│  │       REST API          │   │      Ingestion Pipeline          │  │
│  │  /api/analytics/*       │   │  Parser Registry → Normalizer    │  │
│  │  /api/transactions      │   │  (+ transfer/investment flags)   │  │
│  │  /api/categories        │   │  → Categorizer → Dedup → SQLite  │  │
│  │  /api/upload  /api/demo  │   └──────────────────────────────────┘  │
│  └─────────────────────────┘                                         │
│  File Watcher (watchdog) — monitors backend/data/watched_folder/     │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Auto-ingestion**: Drop a CSV / PDF / XLS / XLSX bank statement into `backend/data/watched_folder/` and it ingests automatically
- **Manual upload**: Drag-and-drop upload from the dashboard UI
- **Multi-bank support**: HDFC, ICICI, and a generic CSV fallback via a registry pattern; PDF (pdfplumber) and Excel (openpyxl/xlrd) parsers
- **Smart classification**: Auto-detects internal transfers (self top-ups) and investments (Grip, Zerodha, Groww, SIPs…) and keeps them out of "spend"
- **Auto-categorization**: Editable keyword rules assign categories (Food, Transport, Groceries…)
- **Analytics**: Wallet breakdown, category spend, weekly velocity, day-of-week heatmap, top merchants, recurring detection, and plain-English insights
- **Date filtering**: This Month / Last Month / Last 30 Days / This Year / All Time + a custom range clamped to your data
- **Demo mode**: Toggle between your real data and synthetic demo data — perfect for resume/portfolio sharing
- **Deduplication**: Re-importing the same file is safe — file-level and row-level SHA-256 guards prevent duplicates

## The wallet model

This dashboard tracks a **spending wallet** — a secondary account topped up from a
salary account and used for day-to-day spends and investments. Money is *loaded*
in, some is *invested*, the rest is *spent*:

| Term | Meaning |
|---|---|
| **Loaded** | All credits into the account (top-ups, returns, refunds) |
| **Invested** | Debits to broking / MF / SIP platforms |
| **Spent** | Debits that are *not* investments — actual consumption |
| **Unspent** | `Loaded − Invested − Spent` — still in the wallet |

Every spend analytic excludes internal transfers and investments, so totals
reflect real consumption. See [§2 of the docs](docs/DOCUMENTATION.md#2-the-wallet-model-core-concept).

## Setup

Prerequisites: **Python 3.9+**, **Node.js 18+**.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/run.py          # run.py adds src/ to the path itself
```

The server starts at `http://localhost:8000`. Interactive API docs (Swagger) at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app opens at `http://localhost:5173`.

### Generate demo data

```bash
curl -X POST http://localhost:8000/api/demo/generate
```

## Making it your own (new-owner setup)

Taking this over? After the setup above:

1. **A fresh clone starts empty** — the real database is git-ignored, so nothing ships with the repo. To see the dashboard populated immediately, generate synthetic data and toggle **Demo mode** in the UI:
   ```bash
   curl -X POST http://localhost:8000/api/demo/generate
   ```

2. **Configure it for your finances.** Copy the env template and set your details:
   ```bash
   cp backend/config/.env.example backend/config/.env
   ```
   - `ACCOUNT_HOLDER_NAMES` — your name(s) **exactly as they appear in your bank statements**. This drives self-transfer (top-up) detection; without it, your own top-ups get miscounted as income/spend.
   - `INVESTMENT_KEYWORDS` / `CARD_PAYMENT_KEYWORDS` — tune to the platforms you use (defaults live in [config.py](backend/src/app/config.py)).

3. **Import your real data** — drop a CSV / PDF / XLS / XLSX statement into `backend/data/watched_folder/` (auto-ingests) or use the upload button in the UI. Re-importing is safe; duplicates are skipped.

4. **Verify the backend** with the test suite: `cd backend && python -m pytest -q`.

For the full picture — architecture, every endpoint, the data model, and the design rationale — read [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md).

## Project Structure

```
spend-tracker/
├── backend/
│   ├── src/app/
│   │   ├── api/             # FastAPI routers: analytics, transactions, categories, uploads, demo
│   │   ├── ingestion/       # parsers + pipeline
│   │   │   ├── base.py          # abstract BaseParser
│   │   │   ├── registry.py      # routes a file to the right parser
│   │   │   ├── normalizer.py    # standard schema + transfer/investment flags
│   │   │   ├── pipeline.py      # parse → normalize → categorize → dedup → DB
│   │   │   ├── csv_parsers/     # hdfc.py, icici.py, generic.py
│   │   │   ├── pdf_parsers/     # statement.py (pdfplumber)
│   │   │   └── xlsx_parser.py   # Excel (openpyxl/xlrd)
│   │   ├── categorization/  # keyword-matching engine + default rules
│   │   ├── utils/           # transfers, investments, card_payments, dedup
│   │   ├── watcher/         # watchdog file-system monitor
│   │   ├── demo/            # synthetic data generator
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── config.py        # settings (.env-driven)
│   │   ├── database.py      # engine / session
│   │   └── main.py          # FastAPI app + startup
│   ├── data/                # SQLite db + watched_folder/  (git-ignored)
│   ├── config/.env.example  # copy to config/.env to override defaults
│   ├── scripts/run.py       # entrypoint
│   ├── tests/               # pytest suite
│   └── pytest.ini           # adds src/ to pythonpath
└── frontend/src/
    ├── api/                 # axios client → /api proxy
    ├── components/          # charts, dashboard, layout, shared, transactions, upload
    ├── hooks/               # TanStack Query data hooks
    ├── pages/               # Dashboard, Transactions, Income, Categories
    ├── store/               # Zustand (demo-mode toggle)
    ├── types/ · utils/      # shared types + helpers
```

## API at a glance

Base URL `/api` (Vite proxies to `http://localhost:8000` in dev). Analytics
endpoints accept `mode=real|demo` and optional `start_date` / `end_date`.

| Group | Endpoints |
|---|---|
| Analytics | `/analytics/wallet`, `/summary`, `/by-day` · `/by-week` · `/by-month` · `/by-year`, `/by-category`, `/weekly-velocity`, `/heatmap`, `/top-merchants`, `/recurring`, `/insights` |
| Transactions | `GET /transactions`, `PATCH /transactions/{id}/category`, `DELETE /transactions/{id}` |
| Categories | `GET·POST /categories`, `PATCH·DELETE /categories/{id}` |
| Accounts | `GET·POST /accounts`, `PATCH·DELETE /accounts/{id}` (bank / card sources — see note below) |
| Upload / Demo | `POST /upload`, `POST /demo/generate`, `DELETE /demo/clear` |
| Health | `GET /health` |

Full reference in [§6 of the docs](docs/DOCUMENTATION.md#6-api-reference).

> 🚧 **Multi-account / multi-card** support is being introduced. The foundation has
> shipped — an `Account` entity (bank or card), an `account_id` on every transaction,
> account-aware dedup, and the `/api/accounts` API. Statement-to-account tagging,
> credit-card parsers, per-account analytics, and the selector UI are next, so the
> dashboard still shows one combined view for now.

## Key Design Decisions

**Wallet model over income model**: loaded / invested / spent / unspent buckets, not income/savings — see the docs for why this account type needs it.

**Classification flags**: `is_internal_transfer` and `is_investment` are set at import time; spend analytics exclude both, so "spent" is real consumption.

**Parser Registry pattern**: each parser implements `can_parse(filepath, headers)` and `parse()`. The registry tries parsers in priority order — specific banks first, generic fallback last. Adding a bank needs only a new file.

**`data_mode` on every transaction**: real and demo data coexist in one DB; switching is a single `WHERE data_mode = ?`. The server is stateless — the frontend passes `?mode=demo|real`.

**Amount always positive**: a `transaction_type` column (`debit`/`credit`) carries direction, avoiding signed-amount bugs in `SUM()` aggregations.

**Two-level deduplication**: a file-level SHA-256 skips already-ingested files; a row-level SHA-256 (`account_id + date + amount + description`) UNIQUE constraint silently discards duplicates across overlapping exports — while keeping the same charge seen in two different accounts as two distinct rows.

**React Query keys include `mode`**: every key is `["analytics", "summary", mode, range]`, so toggling demo mode invalidates and refetches all data automatically.

## Running Tests

```bash
cd backend
source venv/bin/activate
python -m pytest -q          # pytest.ini adds src/ to the path
```

## Adding a New Bank

1. Create `backend/src/app/ingestion/csv_parsers/yourbank.py`
2. Subclass `BaseParser`; implement `can_parse()` (inspect your bank's unique column headers) and `parse()` (return a `list[RawTransaction]`)
3. Register it in `backend/src/app/ingestion/registry.py` — add an instance to `_PARSERS` **before** `GenericCsvParser`
