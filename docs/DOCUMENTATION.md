# Spend Tracker — Documentation

_Last updated: July 2026 · single canonical reference_

The complete guide to Spend Tracker — the mental model, every screen, the full
API, backend internals, and how each number is computed.

> **Multi-account / multi-card support.** Shipped: an `Account` entity (bank or
> card), an `account_id` on every transaction, account-aware deduplication, the
> `/api/accounts` CRUD API (§6, §8), **cross-account transfer detection** (§4.1),
> **credit-card statement parsers** for HDFC, SBI, Axis, and American Express (§4.3,
> §7), an **upload-time account picker** (tag a statement to its account on import),
> a **per-account filter** across every analytics endpoint, and an **account selector**
> in the top bar to switch between the combined view and any single bank/card. Still
> open: per-account net-worth/balances. See the [ROADMAP](ROADMAP.md#multi-account--multi-bank).

## Table of contents
1. [Overview](#1-overview)
2. [Core concept — spend vs. everything else](#2-core-concept--spend-vs-everything-else)
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
| Demo mode | Synthetic data for sharing without exposing real finances — ~13 months of spend, income, investments and returns so every page is populated |
| Deduplication | Two-level hash guards prevent double-ingestion |

---

## 2. Core concept — spend vs. everything else

The app answers *"what did I actually spend?"* — which means pulling everything that
**isn't** consumption out of the total. Every **debit** lands in exactly one bucket:

```
   ┌─────────────────────────────────────────────────────────┐
   │                         DEBITS                           │
   └──┬──────────┬───────────┬──────────────┬────────────────┬┘
      ▼          ▼           ▼              ▼                ▼
 ┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────┐ ┌────────┐
 │ SPEND  │ │ INVESTED│ │ TRANSFER │ │ CARD PAYMENT │ │ POKER  │
 │ real   │ │ Grip,MF │ │ own-acct │ │ bank→card    │ │ private│
 │ consum.│ │ SIP,P2P │ │ + washes │ │ bill settle  │ │ game   │
 └────────┘ └─────────┘ └──────────┘ └──────────────┘ └────────┘
   spend      Invest-      excluded       excluded        excluded
   total       ments
```

| Bucket | What it is | Where it shows |
|---|---|---|
| **Spend** | Real consumption — a debit that's none of the below | Spends page, *You spent ₹X* |
| **Invested** | Broking / MF / SIP / P2P outflows (Grip, Zerodha, Groww, INDSTOCKS…) | Investments page (invested vs. returns) |
| **Transfer** | Own-account moves + manually-marked washes (a repaid loan to a friend) | Transactions → Transfers |
| **Card payment** | Bank→card bill settlement — the swipes are the real spend, counted once | excluded |
| **Poker** | Private-game settlements (names in `POKER_KEYWORDS`, set in `.env`) | Transactions → Poker |

**Credits** split the same way — real **income** vs. investment **returns**
(`is_investment` credits), transfers, and card-side settlements — so income isn't
inflated by a redemption or a repaid loan.

**Why it matters:** counting an ₹84k transfer to Grip as "spend," or a repaid ₹2.25L
friend-loan as "income," makes the dashboard lie. Each rupee sits in the right bucket
so "spent" means *actually consumed*.

> **Legacy wallet view.** The tracked account is a *spending wallet* — a secondary
> account topped up from a salary account — and an earlier hero framed it as
> *loaded → invested → spent → unspent* (`Unspent = Loaded − Invested − Spent`, still at
> `/analytics/wallet`). That view was removed when the app was slimmed to Spends +
> Investments; the classification above is the same logic.

---

## 3. Architecture

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
Detector: `backend/src/app/utils/interbank.py`. Reconcile resets the transfer flag on
bank rows before re-deriving pairs, but **skips any row with a `bucket` set** (§4.4),
so poker tags and manual transfer marks survive a re-import.

**c) Manual marking.** Auto-detection can't see third-party washes — e.g. a loan to a
friend that later gets repaid. `PATCH /api/transactions/{id}/transfer?is_transfer=`
sets `is_internal_transfer` and `bucket="transfer"` on a row (a "mark transfer / unmark
transfer" action in the transactions table), excluding it from spend & income; because
it carries a `bucket`, reconcile leaves it alone on the next import.

**b) Name-based (single statement).** When only one account is in play, a credit is
a self-transfer when your own name appears right after a transfer reference:

- ✅ `IMPS-000000000000-YOURNAME-UTIB-…` → top-up (your own money)
- ❌ `NEFT CR-…-EXAMPLE CORP-YOURNAM` → real income (you're only the beneficiary)

Detector: `backend/src/app/utils/transfers.py` · names in `config.py` → `account_holder_names`
(set these to your own name(s) — see `config/.env.example`). Note: for
account-tagged data, the cross-account matcher recomputes this flag, replacing the
name-based guess and avoiding its false positives on incoming payments.

### 4.2 `is_investment` — wealth, not spend
A debit is an investment when it goes to a broking/MF/SIP platform. Three signals:

- ✅ Any UPI handle containing `.BRK@` (`GRIPBROKING.CF.BRK@…`, `INDSTOCKS.ICCL1.BRK@…`)
- ✅ Built-in platform names: Grip, Zerodha, Groww, INDSTOCKS, Smallcase, Kuvera, Upstox, INDmoney…
- ✅ **User-defined payee rules** (`investment_rules` table) — keywords like `LENDBOX`,
  `INDIAN CLEARING` that the app didn't ship knowing, managed from the Investments page.

Built-in detection runs at ingest (`utils/investments.py`; config keywords +
DB rules combined). On top of that, the **Investments page** lets you manage rules
(re-applied to existing **bank** transactions, flag turned ON only so manual tags
survive) and **manually mark/unmark** any bank debit. Investment management is
bank-only — you invest from a bank, not a card. See §5.5.

The flag runs **both directions**: a matching **debit** is money *invested* (kept out
of spend); a matching **credit** is a *return*/redemption (kept out of income, shown
under Investments → Returns) — so a P2P repayment or MF redemption isn't miscounted as
earnings. A platform **label** can span several keywords (e.g. Grip = `GRIP`, `INGENICO`,
`LOANX`, `IRONWELL`, `AKME FINTRADE`, …), so list/breakdown filtering matches by **label**
(any of its keywords), not a single keyword — see the `investment_platform` filter on
`GET /transactions`.

### 4.3 `is_card_payment` — card settlement, not spend or income
Two cases, both kept out of the numbers so card money is counted once:
- A **debit on a bank account** paying a card bill (`CRED CLUB`, `CREDIT CARD`…) —
  excluded from spend (the real consumption is the itemised card charges).
- **Any credit on a card statement** (payment received, cashback, refund) — excluded
  from income; a card never earns income, it only gets settled.

Card *debits* (the charges themselves) are real per-merchant **spend**. Set in the
normalizer (`_CARD_SOURCES`) · bank-side keywords in `config.py` → `card_payment_keywords`.

### 4.4 `bucket` — poker & manual transfers
A nullable **`bucket`** column carries classification that isn't captured by the two
boolean flags (values so far: `"poker"`, `"transfer"`). Both are excluded from spend
and income, and both are addressable via the `kind` filter on `GET /transactions`.

- **Poker** — the import normalizer tags any row whose description matches a name in
  `settings.poker_keywords` with `bucket="poker"` **and** `is_internal_transfer=True`,
  so poker settlements don't distort spend or income and are filterable via `kind=poker`.
  Counterparty names are personal, so they live in `config/.env` as `POKER_KEYWORDS`
  (gitignored, empty default in `config.py`) — not in the repo.
- **Transfer** — a manual mark (§4.1c) sets `bucket="transfer"`.

Because `reconcile_internal_transfers` skips any row with a `bucket` set, these tags are
**re-import-proof** (a prior bug wiped manual marks on every re-import; fixed).

### 4.5 How the flags affect analytics
| Bucket | Internal transfers | Investments | Card payments |
|---|---|---|---|
| **Spend** analytics (all `/analytics/*` except `/wallet`) | excluded | excluded | excluded |
| **Income** views (`/income-*`) | excluded | excluded | excluded |
| **Wallet** view (`/analytics/wallet`) | counted as *Loaded* | counted as *Invested* | counted as *Card bills* |
| **Transactions** list | shown, badged `↔ Internal`, muted | shown | shown |

---

## 5. The screens

The nav is exactly **four tabs: Spends · Transactions · Fixed Spends · Investments**.
The **Income** (`/income`, §5.3) and **Categories** (`/categories`, §5.4) pages were
**removed from the nav** — their routes are still registered and reachable by URL, and
their data and endpoints still exist; they're hidden, not deleted.

The top bar also holds two global scopes that apply to every page: the **demo-mode
toggle** (real vs synthetic data) and the **account selector** — "All accounts" for
the combined view, or any single bank/card to drill in. Switching either re-scopes
and refetches the whole dashboard.

### 5.1 Spends (`/`)
The home page (the old Dashboard, rebuilt clean). Adapts to the selected date range and
shows the actual data window on top (e.g. "Showing 1 Jan 2026 – 24 May 2026"). If the
period has no data, the page collapses to a single empty state.

- **Headline** — *You spent ₹X* for the selected range, with the **transaction count** and **daily average** beneath it.
- **Monthly trend** — a bar chart of spend per month.
- **Recent transactions** — a short list of the latest spends.
- **Account freshness** — each bank/card with its *data-through* date and a colour-coded staleness dot (🟢 ≤7d, 🟡 ≤30d, 🔴 >30d), so you can see which account needs a fresh statement.
- **Date control** — preset pills + a Custom Range picker pre-filled with and clamped to your real data bounds.

(The old wallet/"Unspent in wallet" hero and the patterns/heatmap/insights charts were
removed from this page; the underlying `/analytics/*` endpoints still exist.)

### 5.2 Transactions (`/transactions`)
The source of truth — filterable, sortable, paginated table of every transaction.
- **Kind filter** — segmented tabs **All · Spends · Income · Investments · Transfers · Poker** (backed by `GET /transactions?kind=…`, §6).
- **Search** — a debounced description search box (`search` param, matches anywhere in the description); composes with the kind filter, date range, account, and sort.
- Filter by date range and type (debit/credit).
- **Sort** by clicking the Date or Amount column header (toggles asc/desc).
- **Running total** — the list header shows the summed amount of all matching rows (`total_amount` on the response).
- **Account column** — the row's actual bank/card account name with a 🏦/💳 icon (replaces the old import-file "Source" column).
- **Type column** — a colored tag per row (Spend / Income / Investment / Transfer / Poker / Card payment) derived from the row's flags. This replaces the old per-row category badge + "Change" dropdown; categorization still runs in the backend, it's just no longer surfaced per-row here.
- **Mark / unmark transfer** — a per-row action (`PATCH /transactions/{id}/transfer`, §4.1c) for washes auto-detection misses.

### 5.3 Income (`/income`)
> ℹ️ **Hidden from the nav** — the route and its endpoints still exist and the page is
> reachable by URL, but it's no longer linked (data hidden, not deleted).

> ⚠️ Built for variable/freelance income (stability score, expected-vs-actual,
> diversification, savings trajectory). For a salaried-funded spending wallet these
> are largely **not meaningful** — real income lands in the salary account. Slated
> to be replaced by a Wallet view (§14).

### 5.4 Categories (`/categories`)
> ℹ️ **Hidden from the nav** — like Income, the route/endpoints remain and the page is
> reachable by URL; auto-categorization still runs in the backend, it's just not linked.

Two-panel manager — list on the left (auto-selects first, never empty), editor on
the right. Edit name, colour, and the **keyword rules** that drive
auto-categorisation; create / delete categories. Changes invalidate the
categorisation cache and apply to future imports.

### 5.5 Investments (`/investments`)
Manage what counts as an investment vs. spend (bank accounts only), and track investment
**returns** separately from income. The KPI row shows **total invested**, **total
returns**, and **platform count** — all scoped by a **date-range filter**. An **Invested /
Returns toggle** switches the by-platform breakdown and the transaction list between
outflows (money invested, debits) and inflows (returns/redemptions, credits); each row
has an **Unmark**. A **Monthly invested-vs-returns** chart (grouped bars per month) sits
above, with **platform-picker chips** to scope it to one platform. **Click a platform** in
the breakdown to filter the list, and sort by date or amount — filtering is by platform
**label**, which can span several keywords (e.g. Grip = GRIPX + LoanX + Ironwell + bond
issuers). A **payee-rules** manager (collapsed by default, with delete confirmation) lets
you add keywords (e.g. `LENDBOX`) + an optional display label — matching bank transactions
are reclassified immediately and on every future import. Tagging an outflow as investment
removes it from spend (wallet *Invested* bucket); tagging an inflow keeps it out of income
(it's a return of capital, not earnings), so "spent" and "income" both reflect reality.

### 5.6 Fixed Spends (`/subscriptions`)
Your recurring monthly commitments — **rent, bills (electricity / internet / phone),
EMIs, staff, and subscriptions** — detected by **name** (not by recurrence, so even a
once-seen item shows). Each item carries a **frequency** (monthly / quarterly /
half-yearly / yearly / weekly / variable) and is **normalised to a monthly cost** —
a quarterly broadband plan is divided by 3, a lump-sum "variable" item (e.g. prepaid
electricity recharged irregularly) is averaged over the data window. Lists items
grouped by **type** (Rent / Electricity / Internet / OTT / AI / …) with a headline
**per-month total**, and a manager to add a rule (name + keyword + free-form type +
frequency) or change an existing item's frequency inline. Ships with ~25 common
subscription services pre-loaded; add rent (landlord's name), bills, EMIs yourself.
A rule can carry an optional **min-amount floor**, and **several rules may share one
merchant string** — so a single merchant that hosts more than one bill is split by
amount (e.g. "Airtel Payments Bank" → parents' electricity ≥₹1,000 *and* the phone
bill below it). More-specific (min-amount) rules are matched first. A rule can also
set an explicit **`monthly_amount`** override that wins over frequency normalisation —
for a lump-sum prepaid where you know the monthly rate (e.g. a ₹20,007 maintenance
recharge that's really ₹5,200/month). Spans banks and cards. Everything stays counted as spend — a reporting overlay, not
a reclassification. (API + table are named `subscription*` internally.)

---

## 6. API reference

Base URL `/api` (Vite proxies to `http://localhost:8000` in dev). Analytics
endpoints accept `mode=real|demo`, an optional `account_id` (scope to one
account; omit for the combined view), and optional `start_date` / `end_date` (ISO).

### Analytics — `/api/analytics/*`
| Endpoint | Returns |
|---|---|
| `GET /wallet` | **Loaded / Top-ups / Invested / Spent / Unspent** (the wallet model) |
| `GET /summary` | Total spend, total credits, daily average, top category, txn count — `top_category` is now scoped to the selected date range (was all-time) |
| `GET /by-day` · `/by-week` · `/by-month` · `/by-year` | Spend time-series |
| `GET /by-category` | Spend per category with % share |
| `GET /weekly-velocity` | Per-week spend + week-over-week % change |
| `GET /heatmap` | Avg spend by day-of-week × week-of-month |
| `GET /top-merchants` | Top payees by spend, with count + avg/txn |
| `GET /recurring` | Recurring payments grouped by **normalized merchant** — only those with a **consistent amount** (within 50%) on a **periodic cadence** (≥6 days apart) count, with inferred frequency (weekly/monthly/quarterly) + next-due estimate |
| `GET /income-monthly` · `/income-sources` · `/savings-trajectory` | Income views (see §5.3 caveat) |
| `GET /insights` | Plain-English spending insights |

> Every endpoint except `/wallet` reports **real consumption only** — internal
> transfers and investments are excluded.

### Transactions — `/api/transactions`
| Endpoint | Purpose |
|---|---|
| `GET ""` | Paginated list; filters: `mode`, `account_id`, `start_date`, `end_date`, `category_id`, `kind` (`spend`\|`income`\|`investment`\|`transfer`\|`poker`), `transaction_type` (pattern-validated `debit`\|`credit`), `is_investment`, `investment_platform` (by platform label), `search` (description contains), `page`, `page_size`; sort: `sort_by` (`date`\|`amount`), `sort_dir` (`asc`\|`desc`). Response includes `total_amount` — the summed amount of **all** matching rows, not just the current page. Each row carries a nested `account` object. `kind` derives from the flags: `spend` = debits that aren't investments/transfers/card-payments, `income` = the credit equivalent, `investment` = `is_investment`, `transfer` = auto + manually-marked transfers (bucket ≠ poker), `poker` = `bucket="poker"` |
| `POST /reconcile-transfers` | (Re)detect transfers between your own accounts and flag both sides; returns the matched pairs (§4.1). Skips rows with a `bucket` set, so manual marks survive |
| `PATCH /{id}/category` | Re-assign a transaction's category |
| `PATCH /{id}/investment?is_investment=` | Manually mark/unmark as investment (§4.2) |
| `PATCH /{id}/transfer?is_transfer=` | Manually mark/unmark as a transfer — sets `is_internal_transfer` and `bucket="transfer"` (§4.1c) |
| `DELETE /{id}` | Delete a transaction |

### Investments — `/api/investment-rules` · `/api/investments`
| Endpoint | Purpose |
|---|---|
| `GET /investment-rules` · `POST` · `DELETE /{id}` | Manage payee keywords (+ optional display `label`, e.g. keyword `INGENICO` → label `Grip`); creating one re-tags matching bank transactions |
| `POST /investment-rules/apply` | Re-apply all rules to existing bank transactions (flag ON only) |
| `GET /investments/summary` | Total + count + by-platform breakdown of `is_investment` rows for one `direction` (`debit` = invested, `credit` = returns; default `debit`); optional `account_id`, `start_date`, `end_date`. A platform label can span several keywords, so the breakdown is grouped by label |
| `GET /investments/monthly` | Per-month invested-vs-returns for the comparison chart (`{month, invested, returns}`), plus the full `platforms` list for the picker chips; optional `platform` scopes to one label, plus `account_id`, `start_date`, `end_date` |

### Subscriptions — `/api/subscription-rules` · `/api/subscriptions`
| Endpoint | Purpose |
|---|---|
| `GET /subscription-rules` · `POST` · `PATCH /{id}` · `DELETE /{id}` | Manage tracked items (name, keyword, type, frequency, optional `min_amount` + `monthly_amount` override) |
| `GET /subscriptions/summary` | Detected items grouped by service + type, each normalised to a monthly cost; `monthly_total` headline (optional `account_id`) |

### Categories — `/api/categories`
`GET ""` · `POST ""` · `PATCH /{id}` · `DELETE /{id}`

### Accounts — `/api/accounts`
The bank accounts and credit cards you own. Each transaction links to one via
`account_id`, and the transaction list now returns a nested `account` object
(`id · name · type`).

| Endpoint | Purpose |
|---|---|
| `GET ""` | List accounts (ordered by type, then name) |
| `GET /status` | Per-account freshness: latest transaction date + transaction count (which statement to pull next) |
| `POST ""` | Create — `name` (unique), `type` ∈ {`bank`, `card`}, optional `issuer`, `last4` |
| `PATCH /{id}` | Update any field |
| `DELETE /{id}` | Delete — linked transactions survive, their `account_id` is set null |

`account_id` is a query filter on the analytics endpoints and the transactions list
(omit for the combined view), and the transactions list returns a nested `account`
object on each row.

### Upload / Demo / Health
- `POST /api/upload` (multipart, `?mode=real|demo&account_id=<id>`) → runs ingestion, tagging the rows to `account_id` if given; `GET /api/ingest-log[/{id}]`
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
   → Normalizer        (standard schema; sets is_internal_transfer / is_investment / is_card_payment; tags poker rows bucket="poker")
   → Categorizer       (keyword match → category_id)
   → Dedup guard       (SHA-256 row hash UNIQUE, scoped per account; in-file repeats kept)
   → SQLite
   → Reconcile         (re-pair cross-account bank transfers, skipping any bucket-tagged row; §4.1)
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
decrypted with `pypdf` before parsing. The HDFC card parser strips a misleading
leading `EMI ` label that HDFC prints on some full (non-installment) charges, so the
description is the real merchant name. HDFC "payment received" lines extract with a
**blank description** — these now parse as a credit labelled `PAYMENT RECEIVED` (treated
as a card payment and excluded) instead of defaulting to a debit/spend.

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
upgrades without losing data. This is how the `transactions.account_id` and the newer
`transactions.bucket` (§4.4) columns land on existing databases. (Alembic is a
dependency but is not currently wired up.)

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
| `bucket` | nullable — `poker` / `transfer`; extra classification, re-import-proof (§4.4) |
| `file_hash` / `row_hash` | dedup guards (SHA-256; `row_hash` includes `account_id`) |
| `created_at` | timestamp |

Indexes: `(date, data_mode)`, `(category_id)`, `(account_id)`.

**`accounts`** — `id · name (unique) · type` (`bank`/`card`) `· issuer · last4 · created_at`
**`categories`** — `id · name · color · keywords_json`
**`investment_rules`** — `id · keyword (unique) · label · created_at` (user-defined investment payees, §4.2)
**`subscription_rules`** — `id · name · keyword · type · frequency · min_amount · monthly_amount · created_at` (tracked fixed-spend items, §5.6; keyword is **not** unique — a merchant can host several bills split by `min_amount`)
**`ingest_log`** — `id · filename · file_hash · parser_used · rows_parsed/inserted/skipped · status · error_message · ingested_at`

---

## 9. Frontend

Stack: **React 19 + TypeScript + Vite + Tailwind CSS + Recharts + TanStack Query v5 + Zustand + React Router**.

**Pages:** `Dashboard.tsx`, `Transactions.tsx`, `Investments.tsx`, `Subscriptions.tsx`, `Income.tsx`, `Categories.tsx`.

**Key components:** `layout/TopBar` + `Layout` (shell + nav), `dashboard/DateRangeFilter`,
`transactions/TransactionTable` + `CategoryBadge`, `upload/FileUploadModal`,
`shared/DemoModeToggle` + `shared/AccountSelector` + `LoadingSpinner`, chart components in `charts/`.

**State:** server state via TanStack Query (cache keys include `mode` **and the
selected `account_id`** so toggling either refetches automatically); two Zustand
stores — `store/demoMode.ts` (real/demo toggle) and `store/selectedAccount.ts` (the
globally-selected account, `null` = all). Data hooks live in `hooks/useAnalytics.ts`,
`hooks/useTransactions.ts`, `hooks/useAccounts.ts`, `hooks/useInvestments.ts`,
`hooks/useSubscriptions.ts`, `hooks/useCategories.ts`; each analytics hook reads the selected account and threads
it through. Axios client (`api/client.ts`) points at the `/api` Vite proxy.

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

**Single-server mode (one process).** The two servers above are a *development*
setup — Vite gives hot-reload + proxies `/api`. To run everything as **one** process
(no Node server at runtime), build the frontend once and let FastAPI serve it:

```bash
cd frontend && npm run build          # produces frontend/dist/
cd ../backend && PORT=8001 python scripts/run.py
# whole app — UI + API — at http://localhost:8001
```

When `frontend/dist/` exists, `main.py` mounts it: static assets under `/assets`,
a catch-all serving `index.html` for SPA routes, and the API/`/docs` still under
`/api` and `/docs`. Rebuild the frontend whenever its code changes. (This block is a
no-op until you build, so the dev two-server flow is unaffected.) The catch-all
**contains the requested path inside `frontend/dist`** — a hardening fix, since a
naive join let a crafted path escape the static root and serve arbitrary files
(including the SQLite DB).

**Changing the ports.** The backend port defaults to `8000` but honours a `PORT`
env var (`PORT=8001 python scripts/run.py`). For the *dev* two-server flow, start
Vite with a matching `VITE_API_PORT` (`VITE_API_PORT=8001 npm run dev`) so its
`/api` proxy points at the backend. Useful when something else already owns `8000`.

**Binding host.** The server binds `127.0.0.1` (localhost only) by **default** —
it serves real financial data with no auth, so it shouldn't be exposed on the LAN.
Override with the `HOST` env var (`HOST=0.0.0.0 …`) only when you deliberately want
it reachable from other machines.

---

## 11. Testing

```bash
cd backend && python -m pytest -q     # 45 passing
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
| 🟢 | Multi-account & multi-card — _largely shipped:_ Account entity, account-aware dedup, accounts API, cross-account transfer matching, credit-card parsers (HDFC/SBI/Axis/Amex), upload-time account picker, per-account analytics filter + account selector. Remaining: per-account net-worth/balances |
| 🟢 | Investment management — _shipped:_ payee rules + manual tagging + Investments page separate investments from spend (§5.5). Was the main driver of inflated "spend". |
| 🟢 | Subscriptions tracker — _shipped:_ name-based detection + types (OTT/AI/…) + Subscriptions page (§5.6). Stricter recurring detection (consistent amount + cadence). |
| 🔴 P0 | Bulk-categorize queue — clear the 72% uncategorized fast |
| 🔴 P0 | Merchant normalization (collapse brand variants) |
| 🟠 P1 | "Big purchases — identify these" strip for large one-offs |
| 🟠 P1 | Committed-monthly-outflow number (subscriptions + SIPs) |
| 🟢 | Replace Income page with a Wallet view |
| 🟢 | Net-worth / investments-growth view |

Full backlog in [ROADMAP.md](ROADMAP.md) (also tracked in Linear).
