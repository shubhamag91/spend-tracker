import random
import math
import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.categorization.engine import categorize
from app.utils.dedup import row_hash as compute_row_hash

DEMO_MERCHANTS: dict[str, list[tuple[str, float, float]]] = {
    # (merchant_name, mean_amount, std_dev)
    "Food & Dining": [
        ("Zomato Order", 350, 150),
        ("Swiggy Delivery", 280, 120),
        ("Cafe Coffee Day", 180, 60),
        ("Dominos Pizza", 420, 100),
        ("KFC Bangalore", 320, 80),
    ],
    "Transport": [
        ("Uber Ride", 120, 60),
        ("Ola Cab", 100, 50),
        ("Rapido Bike", 50, 20),
        ("BMTC Bus Pass", 500, 0),
        ("IRCTC Train Ticket", 650, 300),
    ],
    "Groceries": [
        ("BigBasket Order", 1400, 500),
        ("Zepto Quick Delivery", 600, 200),
        ("Blinkit Groceries", 800, 300),
        ("DMart Store", 1800, 600),
    ],
    "Shopping": [
        ("Amazon Purchase", 1200, 800),
        ("Flipkart Order", 900, 600),
        ("Myntra Fashion", 1500, 700),
        ("Nykaa Beauty", 700, 300),
    ],
    "Utilities": [
        ("Airtel Prepaid Recharge", 599, 0),
        ("BESCOM Electricity Bill", 900, 300),
        ("JIO Fiber Plan", 999, 0),
    ],
    "Entertainment": [
        ("Netflix Subscription", 649, 0),
        ("Spotify Premium", 119, 0),
        ("BookMyShow Movie", 450, 150),
        ("Hotstar Subscription", 299, 0),
    ],
    "Health": [
        ("PharmEasy Order", 450, 200),
        ("Apollo Pharmacy", 350, 150),
        ("Cult.fit Membership", 2000, 0),
        ("Diagnostic Labs", 800, 300),
    ],
    "Finance": [
        ("Zerodha SIP", 5000, 0),
        ("LIC Premium", 3000, 0),
        ("Groww Investment", 2000, 1000),
    ],
    "Personal Care": [
        ("Naturals Salon", 600, 200),
        ("UrbanCompany Service", 800, 300),
    ],
    "Education": [
        ("Udemy Course", 499, 200),
        ("Coursera Subscription", 2500, 0),
        ("Bookstore Purchase", 350, 150),
    ],
}

# How many transactions per category in 4-week period
CATEGORY_FREQUENCY: dict[str, int] = {
    "Food & Dining": 16,
    "Transport": 20,
    "Groceries": 6,
    "Shopping": 4,
    "Utilities": 2,
    "Entertainment": 3,
    "Health": 2,
    "Finance": 2,
    "Personal Care": 2,
    "Education": 1,
}


def _lognormal_amount(mean: float, std: float) -> float:
    if std == 0:
        return mean
    # Convert to lognormal parameters
    sigma2 = math.log(1 + (std / mean) ** 2)
    mu = math.log(mean) - sigma2 / 2
    return max(10.0, round(random.lognormvariate(mu, math.sqrt(sigma2)), 2))


def generate_demo_data(db: Session) -> int:
    """Generate 13 months of synthetic demo transactions. Idempotent."""
    existing_count = db.query(Transaction).filter(Transaction.data_mode == "demo").count()
    if existing_count > 0:
        return existing_count

    today = date.today()
    start_date = today.replace(day=1) - timedelta(days=365 + 30)
    total_days = (today - start_date).days

    inserted = 0

    def _add(txn_date, amount, ttype, description, *, is_investment=False):
        """Insert one demo transaction (deduped by a salted row_hash)."""
        nonlocal inserted
        rh = compute_row_hash(str(txn_date), amount, description + "_demo_" + uuid.uuid4().hex[:8])
        if db.query(Transaction).filter(Transaction.row_hash == rh).first():
            return
        db.add(Transaction(
            date=txn_date, amount=amount, transaction_type=ttype,
            description=description, raw_description=description,
            category_id=categorize(description, db), source="demo", data_mode="demo",
            file_hash=None, row_hash=rh, is_investment=is_investment,
        ))
        inserted += 1

    # First-of-month anchors across the whole window — used to space out the
    # recurring income / investment / return streams below.
    month_anchors: list[date] = []
    cur = start_date.replace(day=1)
    while cur <= today:
        month_anchors.append(cur)
        cur = (cur.replace(day=28) + timedelta(days=7)).replace(day=1)

    for cat_name, merchants in DEMO_MERCHANTS.items():
        freq_per_4_weeks = CATEGORY_FREQUENCY.get(cat_name, 2)
        total_txns = int(freq_per_4_weeks * total_days / 28)

        for _ in range(total_txns):
            merchant, mean_amt, std_amt = random.choice(merchants)
            amount = _lognormal_amount(mean_amt, std_amt)

            # Random date within the range, weighted toward recent
            days_offset = int(random.triangular(0, total_days, total_days))
            txn_date = start_date + timedelta(days=days_offset)

            description = merchant
            # Add unique salt so each demo transaction gets a distinct row_hash
            rh = compute_row_hash(str(txn_date), amount, description + "_demo_" + uuid.uuid4().hex[:8])
            existing = db.query(Transaction).filter(Transaction.row_hash == rh).first()
            if existing:
                continue

            category_id = categorize(description, db)

            txn = Transaction(
                date=txn_date,
                amount=amount,
                transaction_type="debit",
                description=description,
                raw_description=description,
                category_id=category_id,
                source="demo",
                data_mode="demo",
                file_hash=None,
                row_hash=rh,
            )
            db.add(txn)
            inserted += 1

    # ── Income (credits) — monthly salary + occasional freelance / interest, so the
    #    Income page, diversification, savings and the wallet's "Loaded" aren't empty.
    for i, m in enumerate(month_anchors):
        _add(m + timedelta(days=random.randint(0, 2)),
             round(random.uniform(118000, 132000), 2), "credit", "ACME CORP SALARY CREDIT")
        if i % 2 == 0:
            _add(m + timedelta(days=random.randint(8, 18)),
                 round(random.uniform(15000, 40000), 2), "credit", "Upwork Freelance Payment")
        if i % 3 == 0:
            _add(m + timedelta(days=random.randint(20, 27)),
                 round(random.uniform(800, 2200), 2), "credit", "HDFC Savings Account Interest")

    # ── Investments (debits, is_investment) — recurring SIPs across platforms + the
    #    odd lump sum. Descriptions carry built-in platform keywords so they group by
    #    platform (Zerodha / Groww / Smallcase / Grip).
    sips = [("Zerodha Coin SIP", 10000), ("Groww Mutual Fund SIP", 8000),
            ("Smallcase Investment", 5000), ("Grip Invest SIP", 12000)]
    for m in month_anchors:
        for name, base in sips:
            _add(m + timedelta(days=random.randint(3, 8)),
                 round(base * random.uniform(0.95, 1.05), 2), "debit", name, is_investment=True)
    for m in month_anchors[::3]:
        _add(m + timedelta(days=random.randint(10, 20)),
             round(random.uniform(40000, 90000), 2), "debit", "Grip Invest Lumpsum", is_investment=True)

    # ── Returns (credits, is_investment) — periodic payouts, so the Investments →
    #    Returns view and the monthly invested-vs-returns chart have data.
    for m in month_anchors:
        if random.random() < 0.85:
            _add(m + timedelta(days=random.randint(12, 25)),
                 round(random.uniform(2000, 5000), 2), "credit", "Grip Invest Return", is_investment=True)
        if random.random() < 0.45:
            _add(m + timedelta(days=random.randint(15, 27)),
                 round(random.uniform(3000, 8000), 2), "credit", "Zerodha Coin Redemption", is_investment=True)
        if random.random() < 0.30:
            _add(m + timedelta(days=random.randint(5, 15)),
                 round(random.uniform(500, 1500), 2), "credit", "Smallcase Dividend Payout", is_investment=True)

    db.commit()
    return inserted
