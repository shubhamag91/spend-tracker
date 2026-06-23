# Spend Tracker — Documentation

_Last updated: June 2026 · single canonical reference_

The complete guide to Spend Tracker — the mental model, every screen, the full
API, backend internals, and how each number is computed.

> **🚧 Multi-account / multi-card support is being introduced.** Shipped so far: an
> `Account` entity (bank or card), an `account_id` on every transaction,
> account-aware deduplication, the `/api/accounts` CRUD API (§6, §8),
> **cross-account transfer detection** (§4.1), and **credit-card statement parsers**
> for HDFC, SBI, Axis, and American Express — card charges become per-merchant spend
> while card payments/cashback are kept out of income (§4.3, §7). Still in progress:
> an upload-time account picker (tagging is currently done at import time, not yet in
> the UI), per-account analytics filtering, and the account-selector UI. Until those
> land, the dashboard presents a single combined view across all accounts. See the
> [ROADMAP](ROADMAP.md#multi-account--multi-bank).

## Table of contents
1. [Overview](#1-overview)
2. [The Wallet model](#2-the-wallet-model-core-concept)
3. [Architecture](#3-architecture)
4. [Smart classification (flags)](#4-smart-classification-the-flags)
5. [The screens](#5-the-screens)
6. [API reference](#6-api-reference)
7. [Backend internals](#7-backend-internals)
8. [Data model](#8-data-model)
9. [Frontend](#9-frontend)
10. [Setup & running](#10-setup--running)
11. [Testing](#11-testing)
12. [Key design decisions](#12-key-design-decisions)
13. [Known limitations](#13-known-limitations)
14. [Roadmap](#14-roadmap)

---

## 1. Overview

Spend Tracker ingests bank- and credit-card-statement exports (CSV / XLS / XLSX /
PDF), classifies every transaction, and turns them into a dashboard that answers
three questions:

1. **What are my major spends?**
2. **What are my recurring spends?**
3. **Are there hidden spends I'm not aware of?**

The account being tracked is a **spending wallet** — a secondary account topped up
from a salary account and used for day-to-day spends and investments. This shapes
the entire model (see §2).

**Core capabilities**

| Capability | Description |
|---|---|
| Auto-ingestion | Drop a bank export into `backend/data/watched_folder/` — it ingests automatically |
| Manual upload | Drag-and-drop import from the dashboard |
| Multi-bank support | HDFC, ICICI, and a generic CSV fallback; Excel (XLS/XLSX); PDF bank statements |
| Credit-card statements | Dedicated PDF parsers for HDFC, SBI, Axis, and American Express cards (incl. password-protected) |
| Smart classification | Auto-detects internal transfers (top-ups) and investments (§4) |
| Auto-categorization | Keyword matching assigns categories (Food, Transport, …) |
| Analytics | Wallet breakdown, category spend, weekly velocity, day-of-week heatmap, top merchants, recurring detection, insights |
| Date filtering | This Month / Last Month / Last 30 Days / This Year / All Time + custom range clamped to your data |
| Demo mode | Synthetic data for sharing without exposing real finances |
| Deduplication | Two-level hash guards prevent double-ingestion |

---

## 2. The Wallet model (core concept)

> **Most finance apps assume:** Income → Spend → Savings.
> **This account works differently:** money is *loaded* in, some is *invested*, the rest is *spent*.

```
            ┌─────────────────────────────────────────┐
            │              MONEY LOADED                │
            │  (top-ups from salary a/c + any credits) │
            └───────────────────┬─────────────────────┘
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌────────────┐        ┌────────────┐        ┌────────────┐
   │ INVESTED   │        │   SPENT    │        │  UNSPENT   │
   │ Grip, SIPs │        │ real       │        │ sitting in │
   │ Groww, MF  │        │ consumption│        │ the wallet │
   └────────────┘        └────────────┘        └────────────┘
```

| Term | Definition |
|---|---|
| **Loaded** | All credits into the account (top-ups + salary + returns + refunds) |
| **Top-ups** | Of loaded: self-transfers from your own salary account (`IMPS-…-<yourname>`) |
| **Invested** | Debits to broking / MF / SIP platforms (Grip, Zerodha, Groww, INDSTOCKS…) |
| **Spent** | Debits that are **not** investments — your actual consumption |
| **Unspent** | `Loaded − Invested − Spent` — money still in the wallet |

**Why it matters:** counting an ₹84k transfer to Grip as "spend," or a ₹1.95L
salary top-up as "income," makes the dashboard lie. The wallet model keeps each
rupee in the right bucket so "spent" means *actually consumed*.

Concepts deliberately **absent** because they don't apply to this account type:
savings rate, income stability, income diversification, monthly budgets.

---

## 3. Architecture

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
│  │  /api/accounts          │   │  (dedup scoped per account_id)   │  │
│  │  /api/upload  /api/demo  │   └──────────────────────────────────┘  │
│  └─────────────────────────┘                                         │
│  File Watcher (watchdog) — monitors backend/data/watched_folder/     │
└─────────────────────────────────────────────────────────────────────┘
```

Project layout:
```
spend-tracker/
├── backend/
│   ├── src/app/        # application code (api, ingestion, models, utils…)
│   ├── tests/          # pytest suite
│   ├── data/           # SQLite db + watched_folder/
│   ├── config/         # .env.example
│   ├── scripts/run.py  # entrypoint
│   └── pytest.ini      # adds src/ to pythonpath
├── frontend/src/       # React app (pages, components, hooks, store)
└── docs/               # this file + ROADMAP.md + wireframes/
```

---

## 4. Smart classification (the flags)

Every transaction carries two auto-detected boolean flags, set on import and
back-fillable on existing data.

### 4.1 `is_internal_transfer` — top-ups & self-transfers
Money moved between your own accounts is neither spend nor income. Two detectors
set this flag:

**a) Cross-account matching (precise).** For transactions tagged to an account,
`reconcile_internal_transfers` pairs a *debit* in one account with the matching
*credit* in another (same amount, within 3 days) and flags **both** sides — e.g. a
₹10,00,000 debit in HDFC matched to a ₹10,00,000 credit in Yes Bank the same day.
Runs after every ingestion and on demand via `POST /api/transactions/reconcile-transfers`.
This is the reliable signal once you have ≥2 accounts: an incoming salary/vendor
payment has **no matching debit**, so it is correctly kept as income rather than
mistaken for a self-transfer.
Detector: `backend/src/app/utils/interbank.py`.

**b) Name-based (single statement).** When only one account is in play, a credit is
a self-transfer when your own name appears right after a transfer reference:

- ✅ `IMPS-000000000000-YOURNAME-UTIB-…` → top-up (your own money)
- ❌ `NEFT CR-…-EXAMPLE CORP-YOURNAM` → real income (you're only the beneficiary)

Detector: `backend/src/app/utils/transfers.py` · names in `config.py` → `account_holder_names`
(set these to your own name(s) — see `config/.env.example`). Note: for
account-tagged data, the cross-account matcher recomputes this flag, replacing the
name-based guess and avoiding its false positives on incoming payments.

### 4.2 `is_investment` — wealth, not spend
A debit is an investment when it goes to a broking/MF/SIP platform.

- ✅ Any UPI handle containing `.BRK@` (`GRIPBROKING.CF.BRK@…`, `INDSTOCKS.ICCL1.BRK@…`)
- ✅ Platform names: Grip, Zerodha, Groww, INDSTOCKS, Smallcase, Kuvera, Upstox, INDmoney…

Detector: `backend/src/app/utils/investments.py` · keywords in `config.py` → `investment_keywords`

### 4.3 `is_card_payment` — card settlement, not spend or income
Two cases, both kept out of the numbers so card money is counted once:
- A **debit on a bank account** paying a card bill (`CRED CLUB`, `CREDIT CARD`…) —
  excluded from spend (the real consumption is the itemised card charges).
- **Any credit on a card statement** (payment received, cashback, refund) — excluded
  from income; a card never earns income, it only gets settled.

Card *debits* (the charges themselves) are real per-merchant **spend**. Set in the
normalizer (`_CARD_SOURCES`) · bank-side keywords in `config.py` → `card_payment_keywords`.

### 4.4 How the flags affect analytics
| Bucket | Internal transfers | Investments | Card payments |
|---|---|---|---|
| **Spend** analytics (all `/analytics/*` except `/wallet`) | excluded | excluded | excluded |
| **Income** views (`/income-*`) | excluded | excluded | excluded |
| **Wallet** view (`/analytics/wallet`) | counted as *Loaded* | counted as *Invested* | counted as *Card bills* |
| **Transactions** list | shown, badged `↔ Internal`, muted | shown | shown |

---

## 5. The screens

Four pages, navigated from the top bar: **Dashboard · Transactions · Income · Categories**.

### 5.1 Dashboard (`/`)
Home overview. Adapts to the selected date range and shows the actual data window
on top (e.g. "Showing 1 Jan 2026 – 24 May 2026"). If the period has no data, the
page collapses to a single empty state — no empty tabs.

- **Hero** — the wallet story: *You spent ₹X of ₹Y loaded · ₹Z invested · Unspent ₹W*, with a segmented `[Invested][Spent][Unspent]` bar.
- **KPI strip** — Daily spend · Spend txns · Top category.
- **Tab: Overview** — *Where your money went* (category breakdown) + *Insights*.
- **Tab: Patterns & Trends** — Weekly spend velocity · Day-of-week heatmap · Top merchants · Recurring transactions.
- **Date control** — preset pills + a Custom Range picker pre-filled with and clamped to your real data bounds.

### 5.2 Transactions (`/transactions`)
The source of truth — filterable, sortable, paginated table of every transaction.
- Filter by date range, category, type (debit/credit).
- **Sort** by clicking the Date or Amount column header (toggles asc/desc).
- Inline category change per row.
- Internal transfers (including matched inter-account transfers) badged `↔ Internal` with a muted amount.

### 5.3 Income (`/income`)
> ⚠️ Built for variable/freelance income (stability score, expected-vs-actual,
> diversification, savings trajectory). For a salaried-funded spending wallet these
> are largely **not meaningful** — real income lands in the salary account. Slated
> to be replaced by a Wallet view (§14).

### 5.4 Categories (`/categories`)
Two-panel manager — list on the left (auto-selects first, never empty), editor on
the right. Edit name, colour, and the **keyword rules** that drive
auto-categorisation; create / delete categories. Changes invalidate the
categorisation cache and apply to future imports.

---

## 6. API reference

Base URL `/api` (Vite proxies to `http://localhost:8000` in dev). Analytics
endpoints accept `mode=real|demo` and optional `start_date` / `end_date` (ISO).

### Analytics — `/api/analytics/*`
| Endpoint | Returns |
|---|---|
| `GET /wallet` | **Loaded / Top-ups / Invested / Spent / Unspent** (the wallet model) |
| `GET /summary` | Total spend, total credits, daily average, top category, txn count |
| `GET /by-day` · `/by-week` · `/by-month` · `/by-year` | Spend time-series |
| `GET /by-category` | Spend per category with % share |
| `GET /weekly-velocity` | Per-week spend + week-over-week % change |
| `GET /heatmap` | Avg spend by day-of-week × week-of-month |
| `GET /top-merchants` | Top payees by spend, with count + avg/txn |
| `GET /recurring` | Recurring payments grouped by **normalized merchant** (ref numbers stripped), with inferred cadence (weekly/monthly/quarterly) + next-due estimate |
| `GET /income-monthly` · `/income-sources` · `/savings-trajectory` | Income views (see §5.3 caveat) |
| `GET /insights` | Plain-English spending insights |

> Every endpoint except `/wallet` reports **real consumption only** — internal
> transfers and investments are excluded.

### Transactions — `/api/transactions`
| Endpoint | Purpose |
|---|---|
| `GET ""` | Paginated list; filters: `mode`, `start_date`, `end_date`, `category_id`, `transaction_type`, `page`, `page_size`; sort: `sort_by` (`date`\|`amount`), `sort_dir` (`asc`\|`desc`) |
| `POST /reconcile-transfers` | (Re)detect transfers between your own accounts and flag both sides; returns the matched pairs (§4.1) |
| `PATCH /{id}/category` | Re-assign a transaction's category |
| `DELETE /{id}` | Delete a transaction |

### Categories — `/api/categories`
`GET ""` · `POST ""` · `PATCH /{id}` · `DELETE /{id}`

### Accounts — `/api/accounts`
The bank accounts and credit cards you own. Each transaction links to one via
`account_id`, and the transaction list now returns a nested `account` object
(`id · name · type`).

| Endpoint | Purpose |
|---|---|
| `GET ""` | List accounts (ordered by type, then name) |
| `POST ""` | Create — `name` (unique), `type` ∈ {`bank`, `card`}, optional `issuer`, `last4` |
| `PATCH /{id}` | Update any field |
| `DELETE /{id}` | Delete — linked transactions survive, their `account_id` is set null |

> **Foundation only (in progress).** `account_id` is exposed on transactions but is
> **not yet a query filter**, and analytics endpoints do not yet scope by account.
> Statement-to-account tagging at ingestion is the next step. See the top-of-doc note.

### Upload / Demo / Health
- `POST /api/upload` (multipart, `?mode=real|demo`) → runs ingestion; `GET /api/ingest-log[/{id}]`
- `POST /api/demo/generate` · `DELETE /api/demo/clear`
- `GET /health` → `{"status": "ok"}`

Interactive API docs (Swagger) at `http://localhost:8000/docs`.

---

## 7. Backend internals

Stack: **Python 3.9+**, **FastAPI**, **SQLAlchemy**, **SQLite**, **Pydantic**,
**watchdog**, **openpyxl/xlrd**, **pdfplumber/pypdf**.

### Ingestion pipeline
```
File (CSV / XLS / XLSX / PDF)
   → Parser Registry   (bank CSV → card PDFs → generic PDF/XLSX → generic CSV)
   → RawTransaction[]  (source-specific fields, raw strings)
   → Normalizer        (standard schema; sets is_internal_transfer / is_investment / is_card_payment)
   → Categorizer       (keyword match → category_id)
   → Dedup guard       (SHA-256 row hash UNIQUE, scoped per account; in-file repeats kept)
   → SQLite
   → Reconcile         (re-pair cross-account bank transfers; §4.1)
```
Entry points: the file watcher and the upload API both funnel into the same
pipeline. `run_ingestion(...)` and `normalize_and_insert(...)` accept an optional
`account_id` that is stamped on every inserted row and folded into its dedup hash.
After a successful insert the pipeline calls `reconcile_internal_transfers` so
newly-imported rows are matched against existing ones across accounts.

### Merchant normalization
`app/utils/merchant.py::normalize_merchant` reduces a noisy description
(`UPI-CRED CLUB-CRED.CLUB@AXISB-UTIB0000114-645902607640-PAYMENT ON CRED`) to a
stable payee key (`CRED CLUB`) by stripping transaction-type prefixes, IFSC codes,
VPA handles, reference numbers, and trailing notes. The `/analytics/recurring`
endpoint groups on this key, so the same payee with a different reference each time
collapses into one recurring entry instead of fragmenting.

### Parser registry & adding a source
Each parser implements `can_parse(filepath, headers)` and `parse(filepath)`
(`app/ingestion/base.py`). The registry tries parsers in priority order — specific
banks/cards first, generic fallback last — so adding a source needs only a new file:
1. Create the parser, e.g. `csv_parsers/yourbank.py` or `pdf_parsers/yourcard.py`
2. Subclass `BaseParser`; implement `can_parse()` (inspect unique headers, or for a
   PDF open it and look for an issuer marker) and `parse()` → `list[RawTransaction]`
3. Register it in `ingestion/registry.py` **before** the generic fallbacks
   (CSV parsers route by header; PDF parsers must precede `PdfStatementParser`)

**Credit-card parsers** live in `pdf_parsers/` — `hdfc_card`, `sbi_card`, `axis_card`,
`amex_card`. Each detects its issuer from the first page and parses one transaction
per line; direction comes from an explicit `D`/`C` / `Dr`/`Cr` marker where the
issuer prints one (SBI, Axis) or from keywords otherwise (HDFC, Amex). Any source
listed in the normalizer's `_CARD_SOURCES` has its credits treated as card
settlement, not income (§4.3). Password-protected statements (e.g. Axis) are
decrypted with `pypdf` before parsing.

### Categorization engine
`app/categorization/` — categories + keyword lists seeded from `rules.py` at
startup. The engine lowercases the description and matches keyword lists in order;
first match wins, unmatched → **Uncategorized**. Editable at runtime via the
Categories API (cache invalidated on change).

### File watcher
`app/watcher/file_watcher.py` uses `watchdog` to monitor
`backend/data/watched_folder/`; new files auto-ingest. Formats: `.csv`, `.xlsx`, `.xls`.

### Demo mode
`app/demo/generator.py` creates synthetic transactions under `data_mode='demo'`.
Every query takes `?mode=demo|real` → a `WHERE data_mode = ?` clause; the server
is stateless. The frontend Zustand store includes `mode` in every query key.

### Deduplication
- **File hash** — SHA-256 of the file in `ingest_log`; re-ingesting a file is a no-op.
- **Row hash** — SHA-256 of `(account_id, date, amount, description)` as a UNIQUE
  constraint; overlapping date-range exports skip duplicates silently. Including
  `account_id` means the *same* charge (same date / amount / description) seen in two
  different accounts — e.g. a ₹200 Swiggy order on both your HDFC and Yes Bank — is
  kept as two rows instead of being silently collapsed into one.
- **In-file repeats** — a single statement can legitimately list the same charge
  more than once (e.g. four identical ₹2,000 card charges in a day). The Nth repeat
  within one file gets an occurrence suffix on its row hash so it survives, while
  re-importing the same file still reproduces the suffixes and dedups.

### Schema migrations
Tables are created with `Base.metadata.create_all` at startup, which builds *new*
tables but never ALTERs an existing one. `app/migrations.py::run_migrations(engine)`
(called right after `create_all`) closes that gap for additive columns — it inspects
each table and adds any missing column in place, so an already-populated SQLite DB
upgrades without losing data. This is how the `transactions.account_id` column lands
on existing databases. (Alembic is a dependency but is not currently wired up.)

---

## 8. Data model

**`transactions`**
| Column | Notes |
|---|---|
| `id` | PK |
| `date` | transaction date |
| `amount` | always positive |
| `transaction_type` | `debit` / `credit` |
| `description` / `raw_description` | cleaned / original payee |
| `category_id` | FK → categories (null = Uncategorized) |
| `account_id` | FK → accounts (null = untagged); `ON DELETE SET NULL` |
| `source` | parser that produced it |
| `data_mode` | `real` / `demo` |
| `is_internal_transfer` | top-up / self-transfer flag (§4.1) |
| `is_investment` | investment-outflow flag (§4.2) |
| `is_card_payment` | credit-card bill-settlement flag (debits only) |
| `file_hash` / `row_hash` | dedup guards (SHA-256; `row_hash` includes `account_id`) |
| `created_at` | timestamp |

Indexes: `(date, data_mode)`, `(category_id)`, `(account_id)`.

**`accounts`** — `id · name (unique) · type` (`bank`/`card`) `· issuer · last4 · created_at`
**`categories`** — `id · name · color · keywords_json`
**`ingest_log`** — `id · filename · file_hash · parser_used · rows_parsed/inserted/skipped · status · error_message · ingested_at`

---

## 9. Frontend

Stack: **React 19 + TypeScript + Vite + Tailwind CSS + Recharts + TanStack Query v5 + Zustand + React Router**.

**Pages:** `Dashboard.tsx`, `Transactions.tsx`, `Income.tsx`, `Categories.tsx`.

**Key components:** `layout/TopBar` + `Layout` (shell + nav), `dashboard/DateRangeFilter`,
`transactions/TransactionTable` + `CategoryBadge`, `upload/FileUploadModal`,
`shared/DemoModeToggle` + `LoadingSpinner`, chart components in `charts/`.

**State:** server state via TanStack Query (cache keys include `mode` so toggling
demo mode refetches automatically); `store/demoMode.ts` (Zustand) holds the
real/demo toggle. Data hooks live in `hooks/useAnalytics.ts`,
`hooks/useTransactions.ts`, `hooks/useCategories.ts`. Axios client (`api/client.ts`)
points at the `/api` Vite proxy.

---

## 10. Setup & running

Prerequisites: Python 3.9+, Node.js 18+.

```bash
# Backend → http://localhost:8000  (Swagger at /docs)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python scripts/run.py

# Frontend → http://localhost:5173 (or next free port, e.g. 5174)
cd frontend
npm install
npm run dev

# Optional: generate demo data
curl -X POST http://localhost:8000/api/demo/generate
```

**Changing the ports.** The backend port defaults to `8000` but honours a `PORT`
env var (`PORT=8001 python scripts/run.py`). To keep the frontend's `/api` proxy
pointed at it, start Vite with a matching `VITE_API_PORT` (`VITE_API_PORT=8001 npm
run dev`). Useful when something else already owns `8000`.

---

## 11. Testing

```bash
cd backend && python -m pytest -q     # 33 passing
```
- `test_ingestion.py` — parser registry, normalizer, dedup (incl. per-account row-hash), internal-transfer detection
- `test_api.py` — API integration tests (in-memory SQLite), incl. accounts CRUD + account-tagged transactions

`pytest.ini` adds `src/` to `pythonpath` automatically.

---

## 12. Key design decisions

- **Wallet model over income model** — loaded/invested/spent buckets, not income/savings (§2).
- **Classification flags** — `is_internal_transfer` and `is_investment` keep top-ups and wealth out of "spend" (§4).
- **Transfers detected by matching, not just by name** — once data is account-tagged, a self-transfer is identified by a debit↔credit pair across two accounts, which is more precise than name-matching and avoids flagging incoming payments as transfers (§4.1).
- **Parser registry pattern** — bank logic is isolated; the registry is the only place that knows which parsers exist.
- **Amount always positive** — `transaction_type` carries direction; avoids signed-amount bugs in `SUM()`.
- **`data_mode` everywhere** — real and demo coexist in one DB; switching is a single `WHERE`; server stays stateless.
- **Two-level dedup** — file-hash skips processed files; row-hash UNIQUE handles overlapping exports.
- **React Query keys include `mode`** — toggling demo mode invalidates and refetches everything.

---

## 13. Known limitations

From the June 2026 data audit — these shape what the dashboard can show today:
1. **~72% of spend is Uncategorized** — the keyword categorizer only catches big brands; most Indian UPI spend (individuals, local merchants) falls through. → planned: bulk-categorize queue.
2. **Merchant fragmentation** — `SWIGGY / SWIGGY LTD / SWIGGY LIMITED / SWIGGY INSTAMART` count as four merchants, hiding the true total. → *partially addressed:* `/analytics/recurring` now groups by `normalize_merchant` (§7); the same normalization is not yet applied to `/top-merchants` or category rollups.
3. **Large one-off merchant payments** (e.g. a single ~₹35k merchant charge) need a human label — the data can't tell what was bought.
4. **Income page** metrics aren't meaningful for this account type (§5.3).

---

## 14. Roadmap

| Priority | Item |
|---|---|
| 🔴 P0 | Multi-account & multi-card — _in progress;_ shipped: Account entity, account-aware dedup, accounts API, cross-account transfer matching, and credit-card parsers (HDFC/SBI/Axis/Amex). Next: upload-time account tagging UI, per-account analytics + selector UI |
| 🔴 P0 | Bulk-categorize queue — clear the 72% uncategorized fast |
| 🔴 P0 | Merchant normalization (collapse brand variants) |
| 🟠 P1 | "Big purchases — identify these" strip for large one-offs |
| 🟠 P1 | Committed-monthly-outflow number (subscriptions + SIPs) |
| 🟢 | Replace Income page with a Wallet view |
| 🟢 | Net-worth / investments-growth view |

Full backlog in [ROADMAP.md](ROADMAP.md) (also tracked in Linear).
