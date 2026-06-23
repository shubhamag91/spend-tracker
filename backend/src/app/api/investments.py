from __future__ import annotations
import collections
from datetime import date
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
    rule = InvestmentRule(keyword=keyword, label=(body.label or None) and body.label.strip())
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
    start_date: date | None = None,
    end_date: date | None = None,
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
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    txns = q.all()

    # Group by platform. Each keyword maps to a display label — a rule's own label
    # if set (e.g. "INGENICO" → "Grip", since Grip routes through Ingenico), else the
    # keyword title-cased. Config keywords use their title-case. Unmatched (manually
    # tagged) rows fall back to the normalized merchant.
    label_for_keyword: dict[str, str] = {k.upper(): k.title() for k in investment_keywords(db)}
    for r in db.query(InvestmentRule).all():
        if r.label:
            label_for_keyword[r.keyword.upper()] = r.label
    keywords = list(label_for_keyword.keys())

    def platform_for(desc: str):
        up = (desc or "").upper()
        for k in keywords:
            if k in up:
                return label_for_keyword[k], k   # (display label, matched keyword)
        return normalize_merchant(desc), None     # manually tagged, no keyword

    groups: dict[str, dict] = collections.defaultdict(lambda: {"amounts": [], "keywords": collections.Counter()})
    for t in txns:
        label, kw = platform_for(t.description)
        groups[label]["amounts"].append(t.amount)
        if kw:
            groups[label]["keywords"][kw] += 1

    by_platform = sorted(
        (
            PlatformInvest(
                name=label, total=round(sum(g["amounts"]), 2), count=len(g["amounts"]),
                # the keyword to filter this platform's transactions (most common match,
                # else the label itself for manually-tagged groups)
                keyword=(g["keywords"].most_common(1)[0][0] if g["keywords"] else label),
            )
            for label, g in groups.items()
        ),
        key=lambda p: p.total,
        reverse=True,
    )
    return InvestmentSummary(
        total_invested=round(sum(t.amount for t in txns), 2),
        count=len(txns),
        by_platform=by_platform,
    )
