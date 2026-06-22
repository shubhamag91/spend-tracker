from __future__ import annotations
from collections import defaultdict, Counter
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.models.category import Category
from app.utils.merchant import normalize_merchant
from app.schemas.transaction import (
    AnalyticsSummary, TimeSeriesPoint, CategorySpend, InsightItem,
    WeeklyVelocityPoint, HeatmapCell, MerchantSpend, RecurringTransaction,
    IncomeMonthPoint, IncomeSource, SavingsPoint, WalletSummary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _base_debit_query(db, mode, start_date, end_date):
    q = db.query(Transaction).filter(
        Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False,
        Transaction.transaction_type == "debit",
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    return q


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = _base_debit_query(db, mode, start_date, end_date)
    total_spend = q.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar()
    count = q.count()

    # Credits (income/deposits)
    cq = db.query(Transaction).filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "credit")
    if start_date:
        cq = cq.filter(Transaction.date >= start_date)
    if end_date:
        cq = cq.filter(Transaction.date <= end_date)
    total_credits = cq.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar()

    days = 1
    if start_date and end_date:
        days = max(1, (end_date - start_date).days + 1)
    elif count > 0:
        result = db.query(
            func.min(Transaction.date), func.max(Transaction.date)
        ).filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit").first()
        if result and result[0] and result[1]:
            days = max(1, (result[1] - result[0]).days + 1)

    top_row = (
        db.query(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )

    return AnalyticsSummary(
        total_spend=round(float(total_spend), 2),
        total_credits=round(float(total_credits), 2),
        daily_average=round(float(total_spend) / days, 2),
        top_category=top_row[0] if top_row else None,
        transaction_count=count,
    )


@router.get("/by-day", response_model=List[TimeSeriesPoint])
def by_day(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction.date, func.sum(Transaction.amount).label("total")).filter(
        Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit"
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = q.group_by(Transaction.date).order_by(Transaction.date).all()
    return [TimeSeriesPoint(label=str(r.date), total=round(float(r.total), 2)) for r in rows]


@router.get("/by-week", response_model=List[TimeSeriesPoint])
def by_week(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(
        func.strftime("%Y-W%W", Transaction.date).label("week"),
        func.sum(Transaction.amount).label("total"),
    ).filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = q.group_by("week").order_by("week").all()
    return [TimeSeriesPoint(label=r.week, total=round(float(r.total), 2)) for r in rows]


@router.get("/by-month", response_model=List[TimeSeriesPoint])
def by_month(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total"),
    ).filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = q.group_by("month").order_by("month").all()
    return [TimeSeriesPoint(label=r.month, total=round(float(r.total), 2)) for r in rows]


@router.get("/by-year", response_model=List[TimeSeriesPoint])
def by_year(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            func.strftime("%Y", Transaction.date).label("year"),
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
        .group_by("year")
        .order_by("year")
        .all()
    )
    return [TimeSeriesPoint(label=r.year, total=round(float(r.total), 2)) for r in rows]


@router.get("/by-category", response_model=List[CategorySpend])
def by_category(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label("total"),
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit"
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = q.group_by(Category.name, Category.color).order_by(func.sum(Transaction.amount).desc()).all()

    grand_total = sum(float(r.total) for r in rows) or 1.0
    return [
        CategorySpend(
            category=r.name,
            color=r.color,
            total=round(float(r.total), 2),
            percentage=round(float(r.total) / grand_total * 100, 1),
        )
        for r in rows
    ]


@router.get("/insights", response_model=List[InsightItem])
def insights(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    items: list[InsightItem] = []

    # --- spend by category ---
    cat_rows = (
        db.query(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
    )
    if start_date:
        cat_rows = cat_rows.filter(Transaction.date >= start_date)
    if end_date:
        cat_rows = cat_rows.filter(Transaction.date <= end_date)
    cat_rows = cat_rows.group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()

    total_spend = sum(float(r.total) for r in cat_rows) or 1.0

    if cat_rows:
        top = cat_rows[0]
        pct = round(float(top.total) / total_spend * 100, 1)
        icon_type = "warning" if pct > 40 else "info"
        items.append(InsightItem(
            type=icon_type,
            title=f"{top.name} is your biggest spend",
            body=f"₹{float(top.total):,.0f} ({pct}% of total). "
                 + ("Consider setting a budget limit here." if pct > 40 else "This is your dominant category this period."),
        ))

    # --- domestic staff / cash transfers > 30% ---
    informal_cats = {"Domestic Staff", "Miscellaneous Transfers", "Household & Help"}
    informal_total = sum(float(r.total) for r in cat_rows if r.name in informal_cats)
    if informal_total > 0:
        inf_pct = round(informal_total / total_spend * 100, 1)
        items.append(InsightItem(
            type="tip",
            title="Cash & UPI transfers make up " + str(inf_pct) + "% of spend",
            body=f"₹{informal_total:,.0f} went to individual UPI payments. "
                 "These are hard to track — consider consolidating recurring payments like domestic help into a fixed monthly transfer.",
        ))

    # --- credits / income ---
    cq = db.query(func.coalesce(func.sum(Transaction.amount), 0.0), func.count(Transaction.id)).filter(
        Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "credit"
    )
    if start_date:
        cq = cq.filter(Transaction.date >= start_date)
    if end_date:
        cq = cq.filter(Transaction.date <= end_date)
    credit_total, credit_count = cq.first()
    credit_total = float(credit_total)

    if credit_total > 0:
        savings_rate = round((credit_total - total_spend) / credit_total * 100, 1) if credit_total > total_spend else 0
        if savings_rate > 0:
            items.append(InsightItem(
                type="positive",
                title=f"Saving {savings_rate}% of income",
                body=f"Credits: ₹{credit_total:,.0f} — Spend: ₹{total_spend:,.0f}. You're saving ₹{credit_total - total_spend:,.0f} this period. Great discipline!",
            ))
        else:
            overspend = total_spend - credit_total
            items.append(InsightItem(
                type="warning",
                title="Spending exceeds credits this period",
                body=f"You've spent ₹{overspend:,.0f} more than your credits (₹{credit_total:,.0f}). Review your largest categories above.",
            ))

    # --- high frequency small spend ---
    freq_q = (
        db.query(Transaction.date, func.count(Transaction.id).label("cnt"), func.sum(Transaction.amount).label("total"))
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit", Transaction.amount < 200)
    )
    if start_date:
        freq_q = freq_q.filter(Transaction.date >= start_date)
    if end_date:
        freq_q = freq_q.filter(Transaction.date <= end_date)
    small_total = freq_q.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar()
    small_count = freq_q.with_entities(func.count(Transaction.id)).scalar()

    if small_count and small_count > 5:
        items.append(InsightItem(
            type="tip",
            title=f"{small_count} small payments under ₹200",
            body=f"These add up to ₹{float(small_total):,.0f}. Small daily payments (chai, autos, street vendors) can quietly drain your budget.",
        ))

    # --- top 3 reduction suggestions based on discretionary categories ---
    discretionary = {"Food & Dining", "Entertainment", "Shopping", "Personal Care"}
    disc_rows = [r for r in cat_rows if r.name in discretionary]
    if disc_rows:
        names = ", ".join(r.name for r in disc_rows[:3])
        disc_total = sum(float(r.total) for r in disc_rows)
        items.append(InsightItem(
            type="tip",
            title="Discretionary spend: ₹" + f"{disc_total:,.0f}",
            body=f"{names} are flexible categories. A 20% reduction here would save ₹{disc_total * 0.2:,.0f} this period.",
        ))

    return items


# ── Weekly velocity ────────────────────────────────────────────────────────────

@router.get("/weekly-velocity", response_model=List[WeeklyVelocityPoint])
def weekly_velocity(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Transaction.date, Transaction.amount)
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
    )
    if start_date:
        rows = rows.filter(Transaction.date >= start_date)
    if end_date:
        rows = rows.filter(Transaction.date <= end_date)
    rows = rows.all()

    if not rows:
        return []

    # Group by ISO week number relative to the min date
    min_date = min(r.date for r in rows)
    week_totals: dict[int, float] = defaultdict(float)
    for r in rows:
        wk = ((r.date - min_date).days // 7) + 1
        week_totals[wk] += float(r.amount)

    result = []
    prev = None
    for wk in sorted(week_totals):
        total = round(week_totals[wk], 2)
        change = round((total - prev) / prev * 100, 1) if prev and prev > 0 else None
        result.append(WeeklyVelocityPoint(week_label=f"Week {wk}", total=total, change_pct=change))
        prev = total
    return result


# ── Day-of-week heatmap ────────────────────────────────────────────────────────

@router.get("/heatmap", response_model=List[HeatmapCell])
def heatmap(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Transaction.date, Transaction.amount)
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
        .all()
    )
    if not rows:
        return []

    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    buckets: dict[tuple, list] = defaultdict(list)
    for r in rows:
        day_name = DAY_NAMES[r.date.weekday()]
        week_num = ((r.date.day - 1) // 7) + 1
        week_num = min(week_num, 4)
        buckets[(day_name, week_num)].append(float(r.amount))

    cells = []
    for day in DAY_NAMES:
        for wk in range(1, 5):
            vals = buckets.get((day, wk), [])
            avg = round(sum(vals) / len(vals), 2) if vals else 0.0
            cells.append(HeatmapCell(day=day, week_num=wk, total=avg))
    return cells


# ── Top merchants ──────────────────────────────────────────────────────────────

@router.get("/top-merchants", response_model=List[MerchantSpend])
def top_merchants(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            Transaction.description,
            func.coalesce(Category.name, "Uncategorized").label("category"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = (
        q.group_by(Transaction.description, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )
    return [
        MerchantSpend(
            name=r.description[:40],
            category=r.category,
            total=round(float(r.total), 2),
            count=r.cnt,
            avg_per_txn=round(float(r.total) / r.cnt, 2),
        )
        for r in rows
    ]


# ── Recurring transactions ─────────────────────────────────────────────────────

def _as_date(d):
    if isinstance(d, str):
        from datetime import datetime as dt
        return dt.strptime(d[:10], "%Y-%m-%d").date()
    return d


@router.get("/recurring", response_model=List[RecurringTransaction])
def recurring(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    """Recurring spends, grouped by *normalized merchant* (not raw description).

    Raw descriptions carry a unique reference number per transaction, so grouping
    on them never collapses the same payee. We normalize to a merchant key first,
    then surface merchants seen >= 2 times, with a cadence inferred from the gaps
    between occurrences.
    """
    rows = (
        db.query(
            Transaction.description,
            Transaction.amount,
            Transaction.date,
            func.coalesce(Category.name, "Uncategorized").label("category"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.data_mode == mode,
            Transaction.is_internal_transfer == False,
            Transaction.is_investment == False,
            Transaction.is_card_payment == False,
            Transaction.transaction_type == "debit",
        )
        .all()
    )

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[normalize_merchant(r.description)].append(r)

    scored = []
    for merchant, items in groups.items():
        if len(items) < 2:
            continue
        dates = sorted(_as_date(r.date) for r in items)
        amounts = [float(r.amount) for r in items]
        total = sum(amounts)
        # cadence = median gap between consecutive occurrences
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        gaps = [g for g in gaps if g > 0] or [30]
        median_gap = sorted(gaps)[len(gaps) // 2]
        if median_gap <= 10:
            frequency = "weekly"
        elif median_gap <= 45:
            frequency = "monthly"
        else:
            frequency = "quarterly"
        cat_counts = Counter(r.category for r in items)
        scored.append((
            total,
            RecurringTransaction(
                name=merchant,
                category=cat_counts.most_common(1)[0][0],
                amount=round(total / len(amounts), 2),
                frequency=frequency,
                next_due=(dates[-1] + timedelta(days=median_gap)).strftime("%b %d"),
            ),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [rt for _, rt in scored[:10]]


# ── Income breakdown ───────────────────────────────────────────────────────────

@router.get("/income-monthly", response_model=List[IncomeMonthPoint])
def income_monthly(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "credit")
        .group_by("month")
        .order_by("month")
        .all()
    )
    if not rows:
        return []

    avg_actual = sum(float(r.total) for r in rows) / len(rows)
    expected = round(avg_actual, 2)

    return [
        IncomeMonthPoint(month=r.month, actual=round(float(r.total), 2), expected=expected)
        for r in rows
    ]


@router.get("/income-sources", response_model=List[IncomeSource])
def income_sources(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(Transaction.description, func.sum(Transaction.amount).label("total"))
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "credit")
    )
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    rows = q.group_by(Transaction.description).order_by(func.sum(Transaction.amount).desc()).all()

    grand = sum(float(r.total) for r in rows) or 1.0

    def _classify(desc: str) -> str:
        d = desc.lower()
        if any(k in d for k in ["salary", "payroll", "wages", "ctc"]):
            return "salary"
        if any(k in d for k in ["freelance", "client", "invoice", "consulting"]):
            return "freelance"
        if any(k in d for k in ["interest", "dividend", "fd", "rd", "mutual"]):
            return "interest"
        return "other"

    return [
        IncomeSource(
            name=r.description[:40],
            total=round(float(r.total), 2),
            percentage=round(float(r.total) / grand * 100, 1),
            source_type=_classify(r.description),
        )
        for r in rows
    ]


@router.get("/savings-trajectory", response_model=List[SavingsPoint])
def savings_trajectory(
    mode: str = Query("real", pattern="^(real|demo)$"),
    db: Session = Depends(get_db),
):
    income_rows = (
        db.query(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "credit")
        .group_by("month").order_by("month").all()
    )
    spend_rows = (
        db.query(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.data_mode == mode, Transaction.is_internal_transfer == False, Transaction.is_investment == False, Transaction.is_card_payment == False, Transaction.transaction_type == "debit")
        .group_by("month").order_by("month").all()
    )
    income_map = {r.month: float(r.total) for r in income_rows}
    spend_map = {r.month: float(r.total) for r in spend_rows}
    months = sorted(set(income_map) | set(spend_map))

    result = []
    for m in months:
        inc = income_map.get(m, 0.0)
        spd = spend_map.get(m, 0.0)
        saved = max(0.0, inc - spd)
        rate = round(saved / inc * 100, 1) if inc > 0 else 0.0
        result.append(SavingsPoint(month=m, saved=round(saved, 2), rate=rate))
    return result


# ── Wallet view (Loaded → Invested → Spent) ────────────────────────────────────
# This account is a spending wallet: money is loaded from a salary account, some
# goes to investments, the rest is spent. Income / savings-rate framing doesn't
# apply, so this endpoint counts EVERYTHING (no internal-transfer / investment
# exclusions) and splits it into the three meaningful buckets.

@router.get("/wallet", response_model=WalletSummary)
def wallet(
    mode: str = Query("real", pattern="^(real|demo)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    def _filtered(q):
        if start_date:
            q = q.filter(Transaction.date >= start_date)
        if end_date:
            q = q.filter(Transaction.date <= end_date)
        return q

    base = db.query(Transaction).filter(Transaction.data_mode == mode)

    def _sum(q):
        return float(_filtered(q).with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar())

    # Real money in: credits that aren't investment redemptions (your own money returning)
    loaded = _sum(base.filter(Transaction.transaction_type == "credit", Transaction.is_investment == False))
    topups = _sum(base.filter(Transaction.transaction_type == "credit",
                              Transaction.is_internal_transfer == True, Transaction.is_investment == False))
    invested = _sum(base.filter(Transaction.transaction_type == "debit", Transaction.is_investment == True))
    card_bills = _sum(base.filter(Transaction.transaction_type == "debit", Transaction.is_card_payment == True))

    spend_q = _filtered(base.filter(
        Transaction.transaction_type == "debit",
        Transaction.is_investment == False,
        Transaction.is_internal_transfer == False,
        Transaction.is_card_payment == False,
    ))
    spent = float(spend_q.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar())
    spend_txns = spend_q.count()

    return WalletSummary(
        loaded=round(loaded, 2),
        topups=round(topups, 2),
        other_in=round(loaded - topups, 2),
        invested=round(invested, 2),
        spent=round(spent, 2),
        card_bills=round(card_bills, 2),
        unspent=round(loaded - invested - spent - card_bills, 2),
        spend_txns=spend_txns,
    )
