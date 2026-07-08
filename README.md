# Spend Tracker

A full-stack personal finance dashboard that auto-ingests bank- and
credit-card-statement exports (CSV / PDF / XLS / XLSX), classifies every
transaction, and tracks your **spends and investments** separately. Smart
classification keeps investments, transfers, card-bill payments, and other
non-consumption out of the spend total, so "spent" means money you actually
consumed — and investments get their own page (invested vs. returns). Includes a
**demo mode** toggle for sharing without exposing real finances.

> 📖 **Full documentation:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) is the
> single canonical reference — the mental model, every screen, the complete API,
> backend internals, the data model, and how each number is computed.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Frontend                                  │
│  React 19 + TypeScript + Vite + Tailwind + Recharts + TanStack Query │
│  Pages: Spends · Transactions · Fixed Spends · Investments           │
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
- **Credit-card statements**: Dedicated PDF parsers for HDFC, SBI, Axis, and American Express cards (password-protected statements decrypted via pypdf); card charges become per-merchant spend, card payments/cashback stay out of income
- **Smart classification**: Auto-detects internal transfers (self top-ups) and investments (Grip, Zerodha, Groww, SIPs…) and keeps them out of "spend"; a `bucket` column further separates **poker** settlements (config keyword, e.g. `KANSOUWA`) and **manually-marked transfers** (a wash like a loan to a friend that gets repaid), both excluded from spend & income
- **Cross-account transfer detection**: Moves between two of your own accounts are matched (debit↔credit) and excluded from spend & income
- **Per-account view**: Tag each statement to its account on upload; an account selector scopes the whole dashboard to one bank/card or shows them combined
- **Account freshness**: A card on the Spends page shows each account's *data-through* date with a colour-coded staleness dot, so you know which statement to import next
- **Investment management**: A dedicated Investments page with payee rules (e.g. Lendbox, Indian Clearing) + one-click manual tagging keeps investments out of "spend" — for existing and future imports (bank accounts only); a rule can carry a display label so the breakdown shows the real platform (e.g. keyword `INGENICO` → `Grip`). An **Invested / Returns toggle** views outflows (money invested) vs inflows (redemptions/payouts) separately, with KPIs for total invested, total returns, and platform count
- **Fixed-spends tracker**: A dedicated page for recurring monthly commitments — rent, bills (electricity/internet/phone), EMIs, and subscriptions (Netflix, Spotify, Claude…) — detected by name and **normalised to a monthly cost** by each item's billing frequency (quarterly ÷3, variable lump-sums averaged); rules can carry a min-amount floor so one merchant string can be split into multiple bills (e.g. parents' electricity vs phone, both via Airtel Payments Bank), or a fixed monthly-amount override for lump-sum prepaids (e.g. a ₹20,007 maintenance recharge that's really ₹5,200/month)
- **Auto-categorization**: Editable keyword rules assign categories (Food, Transport, Groceries…)
- **Analytics**: Wallet breakdown, category spend, weekly velocity, day-of-week heatmap, top merchants, merchant-normalized recurring detection, and plain-English insights
- **Sortable transactions**: Sort the transactions table by date or amount
- **Date filtering**: This Month / Last Month / Last 30 Days / This Year / All Time + a custom range clamped to your data
- **Demo mode**: Toggle between your real data and synthetic demo data — perfect for resume/portfolio sharing. Demo spans ~13 months of spend, income, investments and returns, so every page (Spends, Transactions, Investments) is populated
- **Deduplication**: Re-importing the same file is safe — file-level and row-level SHA-256 guards prevent duplicates

## What counts as "spend"

The app separates what you actually *consumed* from everything else. A debit is
**spend** only if it isn't one of these:

| Bucket | What it is |
|---|---|
| **Investments** | Money moved to broking / MF / SIP / P2P platforms — tracked on the Investments page (invested vs. returns), not spend |
| **Transfers** | Own-account moves + manually-marked washes (e.g. a loan to a friend that's repaid) |
| **Card payments** | Bank→card bill settlements — the real spend is the itemised card charges, counted once |
| **Poker** | Private-game settlements — neither spend nor income |

So the headline *You spent ₹X* reflects real consumption. (A legacy wallet view —
*loaded → invested → spent → unspent* — still exists at `/analytics/wallet` but isn't
shown in the slimmed-down UI.) See [§2 of the docs](docs/DOCUMENTATION.md#2-core-concept--spend-vs-everything-else).

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

### Single-server mode (one process)

The two servers above are a development setup (Vite gives hot-reload). To run the
whole app — UI + API — from one Python process instead, build the frontend once and
let the backend serve it:

```bash
cd frontend && npm run build              # produces frontend/dist/
cd ../backend && python scripts/run.py    # serves UI + API at http://localhost:8000
```

`main.py` serves `frontend/dist/` when it exists (no Node server needed at runtime);
rebuild after UI changes. The dev two-server flow is unaffected.

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
│   │   │   ├── pdf_parsers/     # statement.py + card parsers: hdfc_card, sbi_card, axis_card, amex_card
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
    ├── pages/               # Dashboard, Transactions, Investments, Subscriptions, Income, Categories
    ├── store/               # Zustand (demo-mode toggle)
    ├── types/ · utils/      # shared types + helpers
```

## API at a glance

Base URL `/api` (Vite proxies to `http://localhost:8000` in dev). Analytics
endpoints accept `mode=real|demo` and optional `start_date` / `end_date`.

| Group | Endpoints |
|---|---|
| Analytics | `/analytics/wallet`, `/summary`, `/by-day` · `/by-week` · `/by-month` · `/by-year`, `/by-category`, `/weekly-velocity`, `/heatmap`, `/top-merchants`, `/recurring`, `/insights` — all accept optional `account_id` |
| Transactions | `GET /transactions` (filters incl. `kind` (`spend`\|`income`\|`investment`\|`transfer`\|`poker`), `transaction_type`, `is_investment`, `investment_platform` (by platform label), `search` + `sort_by`/`sort_dir`; response carries a `total_amount` of all matching rows), `POST /transactions/reconcile-transfers`, `PATCH /transactions/{id}/category`, `PATCH /transactions/{id}/transfer?is_transfer=` (manually mark/unmark a transfer), `DELETE /transactions/{id}` |
| Categories | `GET·POST /categories`, `PATCH·DELETE /categories/{id}` |
| Accounts | `GET·POST /accounts`, `PATCH·DELETE /accounts/{id}`, `GET /accounts/status` (per-account freshness) — bank / card sources, see note below |
| Investments | `GET·POST /investment-rules`, `DELETE /investment-rules/{id}`, `POST /investment-rules/apply`, `GET /investments/summary` & `GET /investments/monthly` (`summary` takes `direction=debit\|credit` for invested vs returns; `monthly` returns invested-vs-returns per month, optionally scoped to one `platform`, for the comparison chart) |
| Subscriptions | `GET·POST /subscription-rules`, `PATCH·DELETE /subscription-rules/{id}`, `GET /subscriptions/summary` |
| Upload / Demo | `POST /upload`, `POST /demo/generate`, `DELETE /demo/clear` |
| Health | `GET /health` |

Full reference in [§6 of the docs](docs/DOCUMENTATION.md#6-api-reference).

> **Multi-account / multi-card.** An `Account` entity (bank or card), an `account_id`
> on every transaction, account-aware dedup, the `/api/accounts` API, cross-account
> transfer matching, credit-card statement parsers (HDFC, SBI, Axis, Amex), an
> upload-time account picker, a per-account `account_id` filter on every analytics
> endpoint, and an account selector in the top bar (combined view, or drill into one
> bank/card). Remaining: per-account net-worth / balances.

## Key Design Decisions

**Wallet model over income model**: loaded / invested / spent / unspent buckets, not income/savings — see the docs for why this account type needs it.

**Classification flags**: `is_internal_transfer` and `is_investment` are set at import time; spend analytics exclude both, so "spent" is real consumption. A nullable `bucket` column tags **poker** and **manually-marked transfers**; reconcile-on-import skips any row with a `bucket` set, so manual marks survive re-imports.

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

## Adding a New Bank or Card

1. Create the parser — `csv_parsers/yourbank.py` for a CSV/XLS bank export, or `pdf_parsers/yourcard.py` for a card statement (see `hdfc_card.py`, `sbi_card.py`, `axis_card.py`, `amex_card.py`)
2. Subclass `BaseParser`; implement `can_parse()` (inspect unique column headers, or for a PDF open it and match an issuer marker) and `parse()` (return a `list[RawTransaction]`)
3. Register it in `backend/src/app/ingestion/registry.py` — add an instance to `_PARSERS` **before** the generic fallbacks (PDF parsers must precede `PdfStatementParser`)
4. For a card, add its `SOURCE_NAME` to `_CARD_SOURCES` in `ingestion/normalizer.py` so its credits are treated as settlement, not income
