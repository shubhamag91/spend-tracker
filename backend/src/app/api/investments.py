from __future__ import annotations
import collections
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.account import Account
from app.models.investment_rule import InvestmentRule
from app.models.transaction import Transaction
from app.schemas.investment import (
    InvestmentRuleOut, InvestmentRuleCreate, InvestmentSummary, PlatformInvest,
)
from app.utils.merchant import normalize_merchant
from app.utils.investments import investment_keywords

router = APIRouter(tags=["investments"])


def _bank_account_ids(db: Session) -> list[int]:
    return [a.id for a in db.query(Account).filter(Account.type == "bank").all()]


def apply_investment_rules(db: Session, mode: str = "real") -> int:
    """Tag bank-account transactions whose description matches any rule keyword as
    investments. Only turns the flag ON, so manual tags/untags are preserved.
    Investments come from bank accounts, so card transactions are left alone."""
    keywords = [r.keyword.upper() for r in db.query(InvestmentRule).all()]
    bank_ids = _bank_account_ids(db)
    if not keywords or not bank_ids:
        return 0
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.data_mode == mode,
            Transaction.account_id.in_(bank_ids),
            Transaction.is_investment == False,
        )
        .all()
    )
    tagged = 0
    for t in txns:
        up = (t.description or "").upper()
        if any(k in up for k in keywords):
            t.is_investment = True
            tagged += 1
    db.commit()
    return tagged


# ── Rules ───────────────────────────────────────────────────────────────────────

@router.get("/investment-rules", response_model=list[InvestmentRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(InvestmentRule).order_by(InvestmentRule.keyword).all()


@router.post("/investment-rules", status_code=201)
def create_rule(body: InvestmentRuleCreate, db: Session = Depends(get_db)):
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=422, detail="Keyword cannot be empty")
    if db.query(InvestmentRule).filter(InvestmentRule.keyword == keyword).first():
        raise HTTPException(status_code=409, detail="That keyword already exists")
    rule = InvestmentRule(keyword=keyword)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    # immediately apply to existing data so the user sees the effect
    tagged = apply_investment_rules(db)
    return {"rule": InvestmentRuleOut.model_validate(rule), "tagged": tagged}


@router.delete("/investment-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(InvestmentRule).filter(InvestmentRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    # note: existing transactions keep their is_investment flag (untag manually)


@router.post("/investment-rules/apply")
def apply_rules(mode: str = Query("real", pattern="^(real|demo)$"), db: Session = Depends(get_db)):
    return {"tagged": apply_investment_rules(db, mode)}


# ── Summary ─────────────────────────────────────────────────────────────────────

@router.get("/investments/summary", response_model=InvestmentSummary)
def investments_summary(
    mode: str = Query("real", pattern="^(real|demo)$"),
    account_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Total invested (debits flagged is_investment) + breakdown by platform."""
    q = db.query(Transaction).filter(
        Transaction.data_mode == mode,
        Transaction.is_investment == True,
        Transaction.transaction_type == "debit",
    )
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    txns = q.all()

    # Group by the matched investment keyword (LENDBOX, INGENICO, INDIAN CLEARING…)
    # so a platform's transactions roll up cleanly; fall back to the normalized
    # merchant for manually-tagged rows that match no keyword.
    keywords = [k.upper() for k in investment_keywords(db)]

    def platform_for(desc: str) -> str:
        up = (desc or "").upper()
        for k in keywords:
            if k in up:
                return k.title()
        return normalize_merchant(desc)

    groups: dict[str, list[float]] = collections.defaultdict(list)
    for t in txns:
        groups[platform_for(t.description)].append(t.amount)

    by_platform = sorted(
        (PlatformInvest(name=k, total=round(sum(v), 2), count=len(v)) for k, v in groups.items()),
        key=lambda p: p.total,
        reverse=True,
    )
    return InvestmentSummary(
        total_invested=round(sum(t.amount for t in txns), 2),
        count=len(txns),
        by_platform=by_platform,
    )
