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
