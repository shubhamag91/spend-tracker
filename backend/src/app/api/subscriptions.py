from __future__ import annotations
import collections
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.subscription_rule import SubscriptionRule
from app.models.transaction import Transaction
from app.schemas.subscription import (
    SubscriptionRuleOut, SubscriptionRuleCreate,
    SubscriptionSummary, SubscriptionItem, TypeBreakdown,
)

router = APIRouter(tags=["subscriptions"])


# ── Rules ───────────────────────────────────────────────────────────────────────

@router.get("/subscription-rules", response_model=list[SubscriptionRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(SubscriptionRule).order_by(SubscriptionRule.type, SubscriptionRule.name).all()


@router.post("/subscription-rules", response_model=SubscriptionRuleOut, status_code=201)
def create_rule(body: SubscriptionRuleCreate, db: Session = Depends(get_db)):
    name, keyword, type_ = body.name.strip(), body.keyword.strip().upper(), body.type.strip() or "Other"
    if not name or not keyword:
        raise HTTPException(status_code=422, detail="Name and keyword are required")
    if db.query(SubscriptionRule).filter(SubscriptionRule.keyword == keyword).first():
        raise HTTPException(status_code=409, detail="That keyword already exists")
    rule = SubscriptionRule(name=name, keyword=keyword, type=type_)
    db.add(rule)
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
    """Detect subscription charges via the rule keywords and roll them up by
    service and type. Subscriptions are real spend — this is a reporting overlay,
    it doesn't change any spend totals."""
    rules = db.query(SubscriptionRule).all()
    if not rules:
        return SubscriptionSummary(total=0, monthly_estimate=0, service_count=0, by_type=[], items=[])

    # spend debits only (exclude transfers / investments / card-bill payments)
    q = db.query(Transaction).filter(
        Transaction.data_mode == mode,
        Transaction.transaction_type == "debit",
        Transaction.is_internal_transfer == False,
        Transaction.is_investment == False,
        Transaction.is_card_payment == False,
    )
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    txns = q.all()

    # First matching rule wins (rules carry their own display name + type).
    by_service: dict[str, list] = collections.defaultdict(list)
    service_meta: dict[str, tuple[str, str]] = {}  # service -> (name, type)
    for t in txns:
        up = (t.description or "").upper()
        for rule in rules:
            if rule.keyword in up:
                by_service[rule.name].append(t)
                service_meta[rule.name] = (rule.name, rule.type)
                break

    items: list[SubscriptionItem] = []
    for service, ts in by_service.items():
        ts_sorted = sorted(ts, key=lambda x: x.date)
        _, type_ = service_meta[service]
        items.append(SubscriptionItem(
            name=service,
            type=type_,
            amount=round(ts_sorted[-1].amount, 2),     # most recent charge
            total=round(sum(t.amount for t in ts), 2),
            count=len(ts),
            last_date=ts_sorted[-1].date.isoformat(),
        ))
    items.sort(key=lambda i: i.amount, reverse=True)

    type_tot: dict[str, list[float]] = collections.defaultdict(list)
    for it in items:
        type_tot[it.type].append(it.total)
    by_type = sorted(
        (TypeBreakdown(type=t, total=round(sum(v), 2), count=len(v)) for t, v in type_tot.items()),
        key=lambda b: b.total, reverse=True,
    )

    return SubscriptionSummary(
        total=round(sum(it.total for it in items), 2),
        monthly_estimate=round(sum(it.amount for it in items), 2),
        service_count=len(items),
        by_type=by_type,
        items=items,
    )
