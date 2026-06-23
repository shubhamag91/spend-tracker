# Spend Tracker — Roadmap

> Status key: `[ ]` planned · `[~]` in progress · `[x]` shipped
> Near-term priorities below mirror §14 of [DOCUMENTATION.md](DOCUMENTATION.md#14-roadmap) (also tracked in Linear).

---

## Now & Next — current priorities

| Priority | Item |
|---|---|
| 🔴 P0 | **Multi-account & multi-card** `[~]` — track multiple banks + credit cards in one dashboard (see the section below for the phase breakdown) |
| 🔴 P0 | **Bulk-categorize queue** — clear the ~72% uncategorized fast |
| 🔴 P0 | **Merchant normalization** `[~]` — `normalize_merchant` collapses payee variants for recurring detection; extend to top-merchants + category rollups |
| 🟠 P1 | **"Big purchases" strip** — surface large one-off payments that need a human label |
| 🟠 P1 | **Committed-monthly-outflow** number — subscriptions (✅ tracked) + SIPs, rolled into one recurring-commitment figure |
| 🟢 | **Replace Income page with a Wallet view** (see note under Shipped) |
| 🟢 | **Net-worth / investments-growth view** |

---

## Shipped

### v1.0 — Foundation ✅

Core ingestion, categorization, and visualization.

- [x] FastAPI backend with SQLAlchemy + SQLite
- [x] HDFC, ICICI, and generic CSV parsers
- [x] XLSX/XLS parser (openpyxl / xlrd)
- [x] PDF parser (pdfplumber)
- [x] Keyword-based auto-categorization engine
- [x] File watcher — drop-and-ingest from `backend/data/watched_folder/`
- [x] Manual upload via drag-and-drop modal
- [x] Two-level deduplication (file hash + row hash)
- [x] React frontend with Tailwind CSS + Recharts
- [x] Spend time-series charts (day / week / month / year)
- [x] Category donut chart
- [x] Summary KPI strip (daily spend, spend txns, top category)
- [x] Date range filtering (Month / Last Month / 30 Days / Year / All)
- [x] Transactions table with category + type filters
- [x] Demo mode — synthetic data for portfolio sharing
- [x] Insights panel — plain-English spending observations

### Since v1.0 — Wallet model, classification & richer analytics ✅

- [x] **Wallet model** — Loaded / Invested / Spent / Unspent buckets (`/analytics/wallet`)
- [x] **Smart classification flags** — `is_internal_transfer` (self top-ups) and `is_investment`, excluded from spend
- [x] **Spending velocity** — per-week spend + week-over-week % change
- [x] **Top merchant list** — aggregate spend by payee, with count + avg/txn
- [x] **Recurring transaction detection** — auto-tagged subscriptions/EMIs + next-due estimate
- [x] **Day-of-week heatmap** — spend by day-of-week × week-of-month
- [x] **Custom date range** — picker pre-filled with and clamped to real data bounds
- [x] **Category management UI** — add / rename / delete categories, colour picker, edit keyword rules
- [x] **Manual re-categorization** — inline category change per transaction row
- [x] **Income page** — sources, regularity, expected-vs-actual, savings trajectory

> ⚠️ **Income page note:** it shipped, but for a salary-funded *spending wallet*
> these income/savings metrics are largely not meaningful (real income lands in the
> salary account). It is slated to be **replaced by a Wallet view** — see Now & Next.

### Multi-account foundation & dashboard features ✅

- [x] **Account model + account-aware dedup + `/api/accounts`** (Phase 1 — see Multi-account section)
- [x] **Cross-account transfer matching** — debit↔credit pairing across accounts, excluded from spend/income
- [x] **Credit-card statement parsers** — HDFC, SBI, Axis, American Express (PDF, incl. password-protected); card charges = spend, card credits excluded from income
- [x] **Recurring detection rewrite** — group by `normalize_merchant` so reference-numbered payees stop fragmenting; inferred weekly/monthly/quarterly cadence
- [x] **Sort transactions by amount** — `sort_by`/`sort_dir` on the API + clickable Date/Amount column headers
- [x] **Upload-time account picker** — tag a statement to its account (or create one) at import; PDF uploads enabled
- [x] **Per-account analytics + selector** — `account_id` filter on all endpoints + a top-bar account selector that scopes the whole dashboard
- [x] **Investment management** — `investment_rules` (user-defined payee keywords) + manual per-transaction tagging + a dedicated Investments page (total invested, by-platform, rules manager); separates investments from spend, bank-only. This was the main driver of the inflated "spend" total.
- [x] **Subscriptions tracker** — `subscription_rules` (name + keyword + type), ~25 services pre-seeded, dedicated Subscriptions page grouping detected services by type (OTT/AI/Music/Productivity/Cloud); reporting overlay, stays counted as spend. Spans banks + cards.
- [x] **Stricter recurring detection** — `/analytics/recurring` now requires a consistent amount and a periodic cadence, dropping unrelated repeat payments to the same payee.

---

## Later

### Categorization (continues the P0 work)
- [ ] **Uncategorized queue** — dedicated view of all unmatched transactions for review
- [ ] **Bulk re-categorization** — select multiple transactions → assign category
- [ ] **Category merge** — combine two categories and re-tag history
- [ ] **Category drill-down** — click a category in the donut → see its transactions
- [ ] **Month-over-month change badges** — "+12% vs last month" on KPI cards

### Multi-account & multi-bank

**Status: `[~]` in progress.** Goal: track **multiple bank accounts + multiple credit cards** in one combined
dashboard, with the option to drill into a single account. Credit cards are modelled
as full per-merchant spends, while the bank→card bill-payment that settles them is
reclassified as an internal transfer (so spend is never double-counted).

**Phase 1 — data-model foundation** ✅ _shipped_
- [x] **Account model** — `accounts` table (`name · type bank|card · issuer · last4`) + CRUD at `/api/accounts`
- [x] **`account_id` on every transaction** — FK (`ON DELETE SET NULL`), exposed in the transactions API
- [x] **Account-aware deduplication** — `account_id` folded into the row-hash so identical charges in different accounts don't collide
- [x] **In-place schema migration** — `app/migrations.py` adds new columns to existing SQLite DBs without data loss

**Phase 2+ — remaining**
- [x] **Cross-account (bank↔bank) transfer matching** — `reconcile_internal_transfers` pairs a debit in one account with the matching credit in another and excludes both from spend/income; runs after ingestion + `POST /transactions/reconcile-transfers`
- [x] **Credit-card statement parsers** — `hdfc_card`, `sbi_card`, `axis_card`, `amex_card` (PDF); password-protected statements decrypted via `pypdf`. Card charges = per-merchant spend; card credits (payment/cashback/refund) excluded from income via `is_card_payment`
- [x] **In-file duplicate handling** — identical repeated charges in one statement are preserved (occurrence-suffixed row hash) instead of collapsing
- [x] **Statement tagging UI** — upload-time account picker (pick existing or create inline; PDF allowed); `account_id` threaded through ingestion. Per-account watched sub-folders still optional.
- [x] **Per-account analytics** — optional `account_id` filter across every analytics endpoint and the transactions list (shared `_mode_acct` helper)
- [x] **Account selector UI** — top-bar selector (Zustand) for combined view or drill into one bank/card; part of every query key so the dashboard re-scopes on switch
- [ ] **Bank↔card reconciliation refinement** — currently the bank's lump card-bill payment is excluded from spend and card charges are counted (no double-count); explicit bank-payment↔card-statement linking is not attempted (CRED aggregates payments)
- [x] **Inter-account transfer detection** — name-based `is_internal_transfer` for single statements; superseded by cross-account matching above for tagged data
- [ ] **Cross-account net-worth snapshot** — needs balance data in statements
- [ ] **New bank parsers** — Kotak, Paytm, PhonePe (Axis & SBI now have card parsers; Yes Bank PDF parses via the generic PDF parser)

### Data export & sharing
- [ ] **CSV export** — download filtered transactions
- [ ] **PDF report** — monthly summary with charts + KPI table
- [ ] **Shareable dashboard link** — time-limited public link showing demo data only
- [ ] **JSON API export** — machine-readable export of all transactions

### Intelligence layer (v2.0)
- [ ] **Anomaly detection** — flag unusually large / out-of-pattern transactions
- [ ] **Spend forecast** — project next month's spend by category
- [ ] **Natural language query** — "How much did I spend on food in March?"
- [ ] **LLM-assisted categorization** — for ambiguous UPI/individual descriptions
- [ ] **Tax-relevant tagging** — flag business expenses / 80C-eligible investments

### Infrastructure & quality
- [ ] **Docker Compose** — single `docker compose up` for the full stack
- [ ] **PostgreSQL option** — swap SQLite for hosted / multi-user deployments
- [ ] **CI pipeline** — GitHub Actions: pytest + ESLint + type-check on every PR
- [ ] **API versioning** — `/api/v1/` prefix for non-breaking evolution
- [ ] **OpenAPI-generated frontend client** — typed client from the FastAPI schema
- [ ] **End-to-end tests** — Playwright golden path (upload → categorize → dashboard)
- [ ] **Performance** — index `transactions(date, data_mode)` for large datasets (10k+ rows)

---

## Out of scope for this account type

The wallet model deliberately omits these — they don't apply to a salary-funded
spending wallet (see [DOCUMENTATION.md §2](DOCUMENTATION.md#2-the-wallet-model-core-concept)):

- **Monthly budgets per category** & over-budget alerts (former v1.4)
- **Savings-rate / savings-goal** tracking
- **Income as a first-class model** (former v1.2) — superseded by the Wallet view

---

## Ideas Backlog (not yet scheduled)

Candidates for future versions; priority depends on user feedback.

- Mobile-responsive layout improvements
- Dark mode
- Recurring bill tracker ("Netflix due on the 15th")
- WhatsApp / SMS transaction parsing
- UPI transaction tagging (Google Pay, PhonePe breakdowns)
- Year-in-review annual summary view
- Multiple currency support
- Family / shared finance view with per-member tagging
