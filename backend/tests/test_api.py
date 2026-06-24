import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Category, Transaction, IngestLog
from app.categorization.rules import DEFAULT_CATEGORIES
from app.categorization.engine import invalidate_cache

_tmp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_file.close()
TEST_DB_URL = f"sqlite:///{_tmp_db_file.name}"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    for cat_data in DEFAULT_CATEGORIES:
        if not db.query(Category).filter(Category.name == cat_data["name"]).first():
            cat = Category(name=cat_data["name"], color=cat_data["color"])
            cat.set_keywords(cat_data["keywords"])
            db.add(cat)
    db.commit()
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    invalidate_cache()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_transactions():
    from datetime import date
    db = TestingSession()
    for i in range(5):
        txn = Transaction(
            date=date(2025, 5, i + 1),
            amount=100.0 * (i + 1),
            transaction_type="debit",
            description=f"Test Transaction {i}",
            source="test",
            data_mode="real",
            row_hash=f"hash_{i}",
        )
        db.add(txn)
    db.commit()
    db.close()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_categories(client):
    r = client.get("/api/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == len(DEFAULT_CATEGORIES)
    assert all("name" in c and "color" in c and "keywords" in c for c in data)


def test_create_category(client):
    r = client.post("/api/categories", json={"name": "Test Cat", "color": "#ff0000", "keywords": ["testshop"]})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Cat"
    assert "testshop" in data["keywords"]


def test_list_transactions_empty(client):
    r = client.get("/api/transactions?mode=real")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_transactions_with_data(client, seed_transactions):
    r = client.get("/api/transactions?mode=real")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5


def test_analytics_summary_empty(client):
    r = client.get("/api/analytics/summary?mode=real")
    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 0.0
    assert data["transaction_count"] == 0


def test_analytics_summary_with_data(client, seed_transactions):
    r = client.get("/api/analytics/summary?mode=real")
    assert r.status_code == 200
    data = r.json()
    assert data["total_spend"] == 1500.0  # 100+200+300+400+500
    assert data["transaction_count"] == 5


def test_analytics_by_month(client, seed_transactions):
    r = client.get("/api/analytics/by-month?mode=real")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["label"] == "2025-05"
    assert data[0]["total"] == 1500.0


def test_demo_generate_and_clear(client):
    r = client.post("/api/demo/generate")
    assert r.status_code == 200
    count = r.json()["transaction_count"]
    assert count > 0

    r2 = client.get("/api/transactions?mode=demo&page_size=1")
    assert r2.json()["total"] == count

    r3 = client.delete("/api/demo/clear")
    assert r3.status_code == 204

    r4 = client.get("/api/transactions?mode=demo&page_size=1")
    assert r4.json()["total"] == 0


def test_accounts_crud(client):
    # empty to start
    assert client.get("/api/accounts").json() == []

    # create a bank and a card
    r = client.post("/api/accounts", json={"name": "HDFC Savings", "type": "bank", "issuer": "HDFC", "last4": "1934"})
    assert r.status_code == 201
    bank = r.json()
    assert bank["name"] == "HDFC Savings" and bank["type"] == "bank" and bank["last4"] == "1934"

    r = client.post("/api/accounts", json={"name": "Amex Card", "type": "card"})
    assert r.status_code == 201

    # list shows both
    accts = client.get("/api/accounts").json()
    assert len(accts) == 2

    # duplicate name rejected
    assert client.post("/api/accounts", json={"name": "HDFC Savings"}).status_code == 409

    # invalid type rejected
    assert client.post("/api/accounts", json={"name": "X", "type": "wallet"}).status_code == 422

    # update
    r = client.patch(f"/api/accounts/{bank['id']}", json={"name": "HDFC Salary"})
    assert r.status_code == 200 and r.json()["name"] == "HDFC Salary"

    # delete
    assert client.delete(f"/api/accounts/{bank['id']}").status_code == 204
    assert len(client.get("/api/accounts").json()) == 1


def test_transaction_carries_account(client):
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    acct = Account(name="Yes Bank", type="bank")
    db.add(acct)
    db.commit()
    db.refresh(acct)
    acct_id = acct.id
    db.add(Transaction(
        date=date(2025, 5, 1), amount=200.0, transaction_type="debit",
        description="SWIGGY", source="test", data_mode="real",
        row_hash="acct_hash_1", account_id=acct_id,
    ))
    db.commit()
    db.close()

    items = client.get("/api/transactions?mode=real&page_size=10").json()["items"]
    tagged = [t for t in items if t["account"] is not None]
    assert len(tagged) == 1
    assert tagged[0]["account"]["name"] == "Yes Bank"
    assert tagged[0]["account"]["type"] == "bank"


def test_transactions_sort_by_amount(client, seed_transactions):
    # seed amounts are 100,200,300,400,500
    asc = client.get("/api/transactions?mode=real&sort_by=amount&sort_dir=asc").json()["items"]
    assert [t["amount"] for t in asc] == [100.0, 200.0, 300.0, 400.0, 500.0]

    desc = client.get("/api/transactions?mode=real&sort_by=amount&sort_dir=desc").json()["items"]
    assert [t["amount"] for t in desc] == [500.0, 400.0, 300.0, 200.0, 100.0]

    # invalid sort field is rejected by the pattern guard
    assert client.get("/api/transactions?mode=real&sort_by=description").status_code == 422


def test_reconcile_interbank_transfers(client):
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    a = Account(name="Bank A", type="bank"); b = Account(name="Bank B", type="bank")
    db.add_all([a, b]); db.commit(); db.refresh(a); db.refresh(b)

    def txn(amount, ttype, acct_id, d, rh):
        return Transaction(date=d, amount=amount, transaction_type=ttype,
                           description=f"{ttype} {amount}", source="test",
                           data_mode="real", row_hash=rh, account_id=acct_id)

    db.add_all([
        # a real transfer: debit in A, matching credit in B one day later -> should pair
        txn(5000.0, "debit", a.id, date(2025, 5, 1), "t1"),
        txn(5000.0, "credit", b.id, date(2025, 5, 2), "t2"),
        # same amount but same account -> NOT a transfer
        txn(5000.0, "credit", a.id, date(2025, 5, 1), "t3"),
        # cross-account but amounts differ -> NOT a transfer
        txn(999.0, "debit", a.id, date(2025, 5, 1), "t4"),
        txn(123.0, "credit", b.id, date(2025, 5, 1), "t5"),
        # cross-account, equal amount, but 30 days apart -> outside window, NOT a transfer
        txn(700.0, "debit", a.id, date(2025, 5, 1), "t6"),
        txn(700.0, "credit", b.id, date(2025, 6, 1), "t7"),
    ])
    db.commit(); db.close()

    r = client.post("/api/transactions/reconcile-transfers?mode=real")
    assert r.status_code == 200
    body = r.json()
    assert body["matched_pairs"] == 1
    assert body["total_amount"] == 5000.0
    assert body["transfers"][0]["from_account"] == "Bank A"
    assert body["transfers"][0]["to_account"] == "Bank B"

    # exactly the two matched rows are flagged internal
    flagged = client.get("/api/transactions?mode=real&page_size=50").json()["items"]
    assert sum(1 for t in flagged if t["is_internal_transfer"]) == 2


def test_normalizer_keeps_in_file_duplicates_and_flags_card_credits(client):
    from datetime import date
    from app.ingestion.base import RawTransaction
    from app.ingestion.normalizer import normalize_and_insert
    db = TestingSession()
    raws = [
        # two identical charges in one statement -> both must survive
        RawTransaction(date(2026, 5, 7), 2.0, "debit", "GOOGLE CLOUD", "sbi_card"),
        RawTransaction(date(2026, 5, 7), 2.0, "debit", "GOOGLE CLOUD", "sbi_card"),
        # a credit on a card statement -> bill settlement, not income
        RawTransaction(date(2026, 5, 14), 7315.0, "credit", "PAYMENT RECEIVED", "sbi_card"),
    ]
    inserted, skipped = normalize_and_insert(raws, db, "fh", "real", account_id=None)
    db.commit()
    assert inserted == 3 and skipped == 0  # the duplicate is kept, not collapsed

    from app.models.transaction import Transaction
    credit = db.query(Transaction).filter(Transaction.transaction_type == "credit").one()
    assert credit.is_card_payment is True  # card credit excluded from income
    db.close()


def test_analytics_scoped_by_account(client):
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    a = Account(name="Acct A", type="bank"); b = Account(name="Acct B", type="card")
    db.add_all([a, b]); db.commit(); db.refresh(a); db.refresh(b)
    db.add_all([
        Transaction(date=date(2025, 5, 1), amount=1000.0, transaction_type="debit",
                    description="A spend", source="t", data_mode="real", row_hash="a1", account_id=a.id),
        Transaction(date=date(2025, 5, 2), amount=250.0, transaction_type="debit",
                    description="B spend", source="t", data_mode="real", row_hash="b1", account_id=b.id),
    ])
    db.commit(); aid, bid = a.id, b.id; db.close()

    combined = client.get("/api/analytics/summary?mode=real").json()
    assert combined["total_spend"] == 1250.0 and combined["transaction_count"] == 2

    only_a = client.get(f"/api/analytics/summary?mode=real&account_id={aid}").json()
    assert only_a["total_spend"] == 1000.0 and only_a["transaction_count"] == 1

    only_b = client.get(f"/api/analytics/summary?mode=real&account_id={bid}").json()
    assert only_b["total_spend"] == 250.0

    # transactions list scoped too
    txns = client.get(f"/api/transactions?mode=real&account_id={bid}").json()
    assert txns["total"] == 1 and txns["items"][0]["description"] == "B spend"


def test_investment_rules_and_manual_toggle(client):
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    bank = Account(name="Bank", type="bank"); card = Account(name="Card", type="card")
    db.add_all([bank, card]); db.commit(); db.refresh(bank); db.refresh(card)
    db.add_all([
        Transaction(date=date(2025, 5, 1), amount=50000.0, transaction_type="debit",
                    description="NET TXN/RAZORPAY/X/LENDBOX", source="t", data_mode="real", row_hash="i1", account_id=bank.id),
        Transaction(date=date(2025, 5, 2), amount=900.0, transaction_type="debit",
                    description="SWIGGY", source="t", data_mode="real", row_hash="i2", account_id=bank.id),
        # a card txn that matches the keyword must NOT be tagged (bank-only)
        Transaction(date=date(2025, 5, 3), amount=100.0, transaction_type="debit",
                    description="LENDBOX something", source="t", data_mode="real", row_hash="i3", account_id=card.id),
    ])
    db.commit(); db.close()

    # spend before
    assert client.get("/api/analytics/summary?mode=real").json()["total_spend"] == 50000.0 + 900.0 + 100.0

    # add a rule -> tags the matching BANK transaction only
    r = client.post("/api/investment-rules", json={"keyword": "LENDBOX"})
    assert r.status_code == 201 and r.json()["tagged"] == 1

    # the Lendbox bank debit leaves spend; card row and Swiggy remain
    assert client.get("/api/analytics/summary?mode=real").json()["total_spend"] == 1000.0
    inv = client.get("/api/investments/summary?mode=real").json()
    assert inv["total_invested"] == 50000.0 and inv["count"] == 1

    # duplicate keyword rejected
    assert client.post("/api/investment-rules", json={"keyword": "LENDBOX"}).status_code == 409

    # manual toggle: mark Swiggy as investment, then unmark
    swiggy = [t for t in client.get("/api/transactions?mode=real").json()["items"] if t["description"] == "SWIGGY"][0]
    assert client.patch(f"/api/transactions/{swiggy['id']}/investment?is_investment=true").status_code == 200
    assert client.get("/api/analytics/summary?mode=real").json()["total_spend"] == 100.0  # only card row left
    client.patch(f"/api/transactions/{swiggy['id']}/investment?is_investment=false")
    assert client.get("/api/analytics/summary?mode=real").json()["total_spend"] == 1000.0

    # is_investment filter on the transactions list
    only_inv = client.get("/api/transactions?mode=real&is_investment=true").json()
    assert only_inv["total"] == 1 and only_inv["items"][0]["description"].endswith("LENDBOX")


def test_investment_summary_direction_splits_invested_and_returns(client):
    """direction=debit totals money invested (outflows); direction=credit totals
    returns/redemptions (inflows). Both sides are is_investment-flagged."""
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    bank = Account(name="Bank", type="bank")
    db.add(bank); db.commit(); db.refresh(bank)
    db.add_all([
        # money invested (debits)
        Transaction(date=date(2025, 5, 1), amount=50000.0, transaction_type="debit",
                    description="LENDBOX SIP", source="t", data_mode="real", row_hash="d1",
                    account_id=bank.id, is_investment=True),
        Transaction(date=date(2025, 5, 2), amount=30000.0, transaction_type="debit",
                    description="LENDBOX SIP", source="t", data_mode="real", row_hash="d2",
                    account_id=bank.id, is_investment=True),
        # a return coming back (credit)
        Transaction(date=date(2025, 6, 1), amount=12000.0, transaction_type="credit",
                    description="LENDBOX REDEMPTION", source="t", data_mode="real", row_hash="c1",
                    account_id=bank.id, is_investment=True),
    ])
    db.commit(); db.close()

    invested = client.get("/api/investments/summary?mode=real&direction=debit").json()
    assert invested["total_invested"] == 80000.0 and invested["count"] == 2

    returns = client.get("/api/investments/summary?mode=real&direction=credit").json()
    assert returns["total_invested"] == 12000.0 and returns["count"] == 1

    # default direction is debit (invested), unchanged from before
    assert client.get("/api/investments/summary?mode=real").json()["count"] == 2

    # bad direction rejected by the pattern validator
    assert client.get("/api/investments/summary?mode=real&direction=sideways").status_code == 422

    # monthly endpoint: invested vs returns per month, for the comparison chart
    monthly = client.get("/api/investments/monthly?mode=real").json()
    by_month = {r["month"]: r for r in monthly["data"]}
    assert by_month["2025-05"]["invested"] == 80000.0 and by_month["2025-05"]["returns"] == 0.0
    assert by_month["2025-06"]["returns"] == 12000.0 and by_month["2025-06"]["invested"] == 0.0

    # picker scoping: the two descriptions land under two platform labels, each one-directional
    assert len(monthly["platforms"]) == 2
    for p in monthly["platforms"]:
        sc = client.get("/api/investments/monthly", params={"mode": "real", "platform": p}).json()
        inv = sum(r["invested"] for r in sc["data"])
        ret = sum(r["returns"] for r in sc["data"])
        assert (inv == 80000.0 and ret == 0.0) or (inv == 0.0 and ret == 12000.0)


def test_recurring_requires_consistent_amount_and_cadence(client):
    from datetime import date
    db = TestingSession()
    def txn(desc, amt, d, rh):
        return Transaction(date=d, amount=amt, transaction_type="debit", description=desc,
                           source="t", data_mode="real", row_hash=rh)
    db.add_all([
        # genuine: same amount, ~monthly -> recurring
        txn("RENT GUY", 40000.0, date(2025, 3, 1), "r1"),
        txn("RENT GUY", 40000.0, date(2025, 4, 1), "r2"),
        txn("RENT GUY", 40000.0, date(2025, 5, 1), "r3"),
        # two unrelated payments to a person: wildly different amounts -> NOT recurring
        txn("RANDO PERSON", 3000.0, date(2025, 3, 5), "r4"),
        txn("RANDO PERSON", 70000.0, date(2025, 4, 8), "r5"),
        # two payments days apart -> NOT recurring (clustered)
        txn("SPLIT PAY", 5000.0, date(2025, 3, 10), "r6"),
        txn("SPLIT PAY", 5200.0, date(2025, 3, 12), "r7"),
    ])
    db.commit(); db.close()

    names = [r["name"] for r in client.get("/api/analytics/recurring?mode=real").json()]
    assert "RENT GUY" in names
    assert "RANDO PERSON" not in names
    assert "SPLIT PAY" not in names


def test_subscriptions_detection_by_type(client):
    from datetime import date
    # default rules aren't seeded in tests; create them explicitly
    assert client.post("/api/subscription-rules", json={"name": "Netflix", "keyword": "netflix", "type": "OTT"}).status_code == 201
    assert client.post("/api/subscription-rules", json={"name": "Claude", "keyword": "anthropic", "type": "AI"}).status_code == 201
    assert client.post("/api/subscription-rules", json={"name": "Netflix", "keyword": "netflix", "type": "OTT"}).status_code == 409  # dup keyword

    db = TestingSession()
    db.add_all([
        Transaction(date=date(2025, 5, 1), amount=649.0, transaction_type="debit", description="NETFLIX SUBSCRIPTION",
                    source="t", data_mode="real", row_hash="s1"),
        Transaction(date=date(2025, 5, 2), amount=2000.0, transaction_type="debit", description="EMI ANTHROPIC CLAUDE SUB",
                    source="t", data_mode="real", row_hash="s2"),
        Transaction(date=date(2025, 5, 3), amount=500.0, transaction_type="debit", description="SWIGGY",
                    source="t", data_mode="real", row_hash="s3"),  # not a subscription
    ])
    db.commit(); db.close()

    s = client.get("/api/subscriptions/summary?mode=real").json()
    assert s["service_count"] == 2
    assert s["window_total"] == 2649.0
    # default frequency is monthly, so monthly == latest charge
    by_type = {b["type"]: b["monthly"] for b in s["by_type"]}
    assert by_type == {"AI": 2000.0, "OTT": 649.0}


def test_subscription_frequency_normalises_to_monthly(client):
    from datetime import date
    # a quarterly broadband plan -> monthly = charge / 3
    r = client.post("/api/subscription-rules", json={
        "name": "Broadband", "keyword": "broadband", "type": "Internet", "frequency": "quarterly"}).json()
    db = TestingSession()
    db.add(Transaction(date=date(2025, 5, 1), amount=3717.0, transaction_type="debit",
                       description="TATA PLAY BROADBAND", source="t", data_mode="real", row_hash="f1"))
    db.commit(); db.close()

    item = client.get("/api/subscriptions/summary?mode=real").json()["items"][0]
    assert item["amount"] == 3717.0           # actual charge unchanged
    assert item["monthly"] == round(3717.0 / 3, 2)  # normalised to monthly

    # change it to monthly via PATCH -> monthly == full charge
    client.patch(f"/api/subscription-rules/{r['id']}", json={"frequency": "monthly"})
    item = client.get("/api/subscriptions/summary?mode=real").json()["items"][0]
    assert item["monthly"] == 3717.0


def test_subscription_min_amount_disambiguates(client):
    from datetime import date
    # two charges share a description; only the big one is the bill we track
    client.post("/api/subscription-rules", json={
        "name": "Parents electricity", "keyword": "airtel payments bank",
        "type": "Electricity", "frequency": "monthly", "min_amount": 1000})
    db = TestingSession()
    db.add_all([
        Transaction(date=date(2025, 5, 16), amount=5200.0, transaction_type="debit",
                    description="AIRTEL PAYMENTS BANK GURGAON UTILITIES", source="t", data_mode="real", row_hash="m1"),
        Transaction(date=date(2025, 5, 14), amount=111.0, transaction_type="debit",
                    description="AIRTEL PAYMENTS BANK GURGAON UTILITIES", source="t", data_mode="real", row_hash="m2"),
    ])
    db.commit(); db.close()

    s = client.get("/api/subscriptions/summary?mode=real").json()
    assert s["service_count"] == 1
    item = s["items"][0]
    assert item["count"] == 1 and item["amount"] == 5200.0 and item["monthly"] == 5200.0


def test_two_rules_same_merchant_split_by_amount(client):
    from datetime import date
    # same merchant string hosts two different bills, split by amount floor
    client.post("/api/subscription-rules", json={
        "name": "Parents electricity", "keyword": "airtel payments bank",
        "type": "Electricity", "frequency": "monthly", "min_amount": 1000})
    r2 = client.post("/api/subscription-rules", json={
        "name": "Phone", "keyword": "airtel payments bank", "type": "Phone", "frequency": "monthly"})
    assert r2.status_code == 201  # same keyword, different floor -> allowed now
    # exact duplicate (same keyword + same floor) still rejected
    assert client.post("/api/subscription-rules", json={
        "name": "Phone dup", "keyword": "airtel payments bank", "type": "Phone"}).status_code == 409

    db = TestingSession()
    db.add_all([
        Transaction(date=date(2025, 5, 16), amount=5200.0, transaction_type="debit",
                    description="AIRTEL PAYMENTS BANK UTILITIES", source="t", data_mode="real", row_hash="x1"),
        Transaction(date=date(2025, 5, 14), amount=111.0, transaction_type="debit",
                    description="AIRTEL PAYMENTS BANK UTILITIES", source="t", data_mode="real", row_hash="x2"),
    ])
    db.commit(); db.close()

    items = {it["type"]: it for it in client.get("/api/subscriptions/summary?mode=real").json()["items"]}
    assert items["Electricity"]["amount"] == 5200.0 and items["Electricity"]["count"] == 1
    assert items["Phone"]["amount"] == 111.0 and items["Phone"]["count"] == 1


def test_subscription_monthly_amount_override(client):
    from datetime import date
    client.post("/api/subscription-rules", json={
        "name": "Maintenance", "keyword": "radius", "type": "Maintenance",
        "frequency": "variable", "monthly_amount": 5200})
    db = TestingSession()
    db.add(Transaction(date=date(2025, 5, 24), amount=20007.0, transaction_type="debit",
                       description="RADIUS SYNERGIES", source="t", data_mode="real", row_hash="mo1"))
    db.commit(); db.close()
    item = client.get("/api/subscriptions/summary?mode=real").json()["items"][0]
    assert item["amount"] == 20007.0 and item["monthly"] == 5200.0  # override wins over variable avg


def test_hdfc_card_strips_bogus_emi_prefix():
    from app.ingestion.pdf_parsers.hdfc_card import _TXN_RE
    import re
    line = "24/05/2026| 14:54 EMI RADIUS SYNERGIES INTERNOIDA C 20,007.70 l"
    m = _TXN_RE.match(line)
    desc = re.sub(r"\s+", " ", m.group(2)).strip().rstrip("+").strip()
    desc = re.sub(r"^EMI\s+", "", desc, flags=re.IGNORECASE)
    assert desc == "RADIUS SYNERGIES INTERNOIDA"


def test_investment_rule_label_in_breakdown(client):
    from datetime import date
    # keyword INGENICO but the real platform is Grip -> label drives the breakdown
    client.post("/api/investment-rules", json={"keyword": "ingenico", "label": "Grip"})
    db = TestingSession()
    db.add(Transaction(date=date(2025, 5, 1), amount=400000.0, transaction_type="debit",
                       description="NET TXN/INGENICOTPV/839/INGENICO", source="t", data_mode="real",
                       row_hash="g1", is_investment=True))
    db.commit(); db.close()
    s = client.get("/api/investments/summary?mode=real").json()
    assert s["total_invested"] == 400000.0
    assert s["by_platform"][0]["name"] == "Grip"


def test_transactions_search_filter(client):
    from datetime import date
    db = TestingSession()
    db.add_all([
        Transaction(date=date(2025, 5, 1), amount=15000.0, transaction_type="debit",
                    description="ACH D- INDIAN CLEARING CORP-X1", source="t", data_mode="real", row_hash="sf1"),
        Transaction(date=date(2025, 5, 2), amount=500.0, transaction_type="debit",
                    description="SWIGGY", source="t", data_mode="real", row_hash="sf2"),
    ])
    db.commit(); db.close()
    r = client.get("/api/transactions?mode=real&search=indian%20clearing").json()
    assert r["total"] == 1 and "INDIAN CLEARING" in r["items"][0]["description"]


def test_accounts_status(client):
    from datetime import date
    from app.models.account import Account
    db = TestingSession()
    a = Account(name="HDFC", type="bank"); b = Account(name="Amex", type="card")
    db.add_all([a, b]); db.commit(); db.refresh(a); db.refresh(b)
    db.add_all([
        Transaction(date=date(2025, 6, 22), amount=100.0, transaction_type="debit", description="x",
                    source="t", data_mode="real", row_hash="st1", account_id=a.id),
        Transaction(date=date(2025, 6, 20), amount=50.0, transaction_type="debit", description="y",
                    source="t", data_mode="real", row_hash="st2", account_id=a.id),
    ])
    db.commit(); db.close()

    status = {s["name"]: s for s in client.get("/api/accounts/status?mode=real").json()}
    assert status["HDFC"]["latest_transaction_date"] == "2025-06-22"
    assert status["HDFC"]["transaction_count"] == 2
    # an account with no transactions still appears, with null date
    assert status["Amex"]["latest_transaction_date"] is None and status["Amex"]["transaction_count"] == 0
