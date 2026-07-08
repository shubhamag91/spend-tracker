from __future__ import annotations
import collections
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.subscription_rule import SubscriptionRule
from app.models.transaction import Transaction
from app.schemas.subscription import (
    SubscriptionRuleOut, SubscriptionRuleCreate, SubscriptionRuleUpdate,
    SubscriptionSummary, SubscriptionItem, TypeBreakdown,
)

router = APIRouter(tags=["subscriptions"])

_VALID_FREQ = {"monthly", "quarterly", "half-yearly", "yearly", "weekly", "variable"}
# how many months one charge covers (for fixed cadences)
_MONTHS_PER_CHARGE = {"monthly": 1.0, "quarterly": 3.0, "half-yearly": 6.0, "yearly": 12.0}


def _validate_freq(f: str) -> None:
    if f not in _VALID_FREQ:
        raise HTTPException(status_code=422, detail=f"frequency must be one of {sorted(_VALID_FREQ)}")


# ── Rules ───────────────────────────────────────────────────────────────────────

@router.get("/subscription-rules", response_model=list[SubscriptionRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(SubscriptionRule).order_by(SubscriptionRule.type, SubscriptionRule.name).all()


@router.post("/subscription-rules", response_model=SubscriptionRuleOut, status_code=201)
def create_rule(body: SubscriptionRuleCreate, db: Session = Depends(get_db)):
    name, keyword, type_ = body.name.strip(), body.keyword.strip().upper(), body.type.strip() or "Other"
    _validate_freq(body.frequency)
    if not name or not keyword:
        raise HTTPException(status_code=422, detail="Name and keyword are required")
    # the same merchant string can host several bills, distinguished by min_amount;
    # only reject an exact duplicate (same keyword AND same amount floor)
    dup = db.query(SubscriptionRule).filter(SubscriptionRule.keyword == keyword)
    dup = dup.filter(SubscriptionRule.min_amount.is_(None) if body.min_amount is None
                     else SubscriptionRule.min_amount == body.min_amount)
    if dup.first():
        raise HTTPException(status_code=409, detail="That keyword + amount rule already exists")
    rule = SubscriptionRule(name=name, keyword=keyword, type=type_, frequency=body.frequency,
                            min_amount=body.min_amount, monthly_amount=body.monthly_amount)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/subscription-rules/{rule_id}", response_model=SubscriptionRuleOut)
def update_rule(rule_id: int, body: SubscriptionRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(SubscriptionRule).filter(SubscriptionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.frequency is not None:
        _validate_freq(body.frequency)
        rule.frequency = body.frequency
    if body.type is not None:
        rule.type = body.type.strip() or "Other"
    if body.name is not None:
        rule.name = body.name.strip() or rule.name
    if body.min_amount is not None:
        rule.min_amount = body.min_amount if body.min_amount > 0 else None
    if body.monthly_amount is not None:
        rule.monthly_amount = body.monthly_amount if body.monthly_amount > 0 else None
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/subscription-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(SubscriptionRule).filter(SubscriptionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ── Summary ─────────────────────────────────────────────────────────────────────

@router.get("/subscriptions/summary", response_model=SubscriptionSummary)
def subscriptions_summary(
    mode: str = Query("real", pattern="^(real|demo)$"),
    account_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Detect fixed-spend charges via rule keywords and normalise each to a
    monthly cost using its frequency (quarterly /3, yearly /12, etc.). Variable
    (lump-sum) items are averaged over the data window. Reporting overlay only —
    these stay counted as spend."""
    from app.models.cash_expense import CashExpense
    rules = db.query(SubscriptionRule).all()
    has_cash = db.query(CashExpense.id).filter(CashExpense.active == True).first() is not None  # noqa: E712
    empty = SubscriptionSummary(monthly_total=0, window_total=0, service_count=0, by_type=[], items=[])
    if not rules and not has_cash:
        return empty

    base = [
        Transaction.data_mode == mode,
        Transaction.transaction_type == "debit",
        Transaction.is_internal_transfer == False,
        Transaction.is_investment == False,
        Transaction.is_card_payment == False,
    ]
    if account_id is not None:
        base.append(Transaction.account_id == account_id)
    txns = db.query(Transaction).filter(*base).all()
    if not txns and not has_cash:
        return empty

    # data window in months, used to average "variable" lump-sum items
    span = db.query(func.min(Transaction.date), func.max(Transaction.date)).filter(*base).first()
    window_months = 1.0
    if span and span[0] and span[1]:
        window_months = max(1.0, (span[1] - span[0]).days / 30.44)

    # Evaluate more-specific rules (with an amount floor) before generic ones, so a
    # ₹5,200 "Airtel Payments Bank" charge matches the ≥₹1,000 rule, not a generic one.
    rules = sorted(rules, key=lambda r: (r.min_amount is not None, r.min_amount or 0), reverse=True)

    by_service: dict[str, list] = collections.defaultdict(list)
    meta: dict[str, SubscriptionRule] = {}
    for t in txns:
        up = (t.description or "").upper()
        for rule in rules:
            if rule.keyword in up and (rule.min_amount is None or t.amount >= rule.min_amount):
                by_service[rule.name].append(t)
                meta[rule.name] = rule
                break

    def monthly_cost(rule: SubscriptionRule, latest: float, total: float) -> float:
        if rule.monthly_amount:           # explicit override wins
            return rule.monthly_amount
        if rule.frequency == "weekly":
            return latest * 52 / 12
        if rule.frequency == "variable":
            return total / window_months
        return latest / _MONTHS_PER_CHARGE.get(rule.frequency, 1.0)

    items: list[SubscriptionItem] = []
    for service, ts in by_service.items():
        ts_sorted = sorted(ts, key=lambda x: x.date)
        rule = meta[service]
        latest = ts_sorted[-1].amount
        total = sum(t.amount for t in ts)
        items.append(SubscriptionItem(
            name=service, type=rule.type, frequency=rule.frequency,
            monthly=round(monthly_cost(rule, latest, total), 2),
            amount=round(latest, 2), total=round(total, 2),
            count=len(ts), last_date=ts_sorted[-1].date.isoformat(),
        ))
    # Cash expenses (cook, maid, …) are recurring debits generated from CashExpense
    # rows; they don't match a subscription rule, so add them as first-class items.
    from app.models.cash_expense import CashExpense
    from app.utils.cash_expenses import CASH_SOURCE
    for e in db.query(CashExpense).filter(CashExpense.active == True).all():  # noqa: E712
        ets = sorted((t for t in txns if t.source == CASH_SOURCE and (t.description or "") == e.name),
                     key=lambda x: x.date)
        items.append(SubscriptionItem(
            name=e.name, type=e.type, frequency=e.frequency, monthly=round(e.amount, 2),
            amount=round(ets[-1].amount if ets else e.amount, 2),
            total=round(sum(t.amount for t in ets), 2), count=len(ets),
            last_date=ets[-1].date.isoformat() if ets else None,
        ))

    items.sort(key=lambda i: i.monthly, reverse=True)

    type_tot: dict[str, list[float]] = collections.defaultdict(list)
    for it in items:
        type_tot[it.type].append(it.monthly)
    by_type = sorted(
        (TypeBreakdown(type=t, monthly=round(sum(v), 2), count=len(v)) for t, v in type_tot.items()),
        key=lambda b: b.monthly, reverse=True,
    )

    return SubscriptionSummary(
        monthly_total=round(sum(it.monthly for it in items), 2),
        window_total=round(sum(it.total for it in items), 2),
        service_count=len(items),
        by_type=by_type,
        items=items,
    )
