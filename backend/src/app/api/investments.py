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


def _platform_labeler(db: Session):
    """Return a fn desc -> (display_label, matched_keyword). Each keyword maps to a
    display label — a rule's own label if set (e.g. INGENICO → Grip), else the keyword
    title-cased. Unmatched (manually tagged) rows fall back to the normalized merchant."""
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

    return platform_for


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
    direction: str = Query("debit", pattern="^(debit|credit)$"),
    account_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Total + per-platform breakdown of is_investment transactions for one direction:
    debit = money invested (outflows), credit = returns/redemptions (inflows)."""
    q = db.query(Transaction).filter(
        Transaction.data_mode == mode,
        Transaction.is_investment == True,
        Transaction.transaction_type == direction,
    )
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    txns = q.all()

    platform_for = _platform_labeler(db)
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


@router.get("/investments/monthly")
def investments_monthly(
    mode: str = Query("real", pattern="^(real|demo)$"),
    platform: str | None = None,   # optional: scope to one platform label (else all)
    account_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Per-month invested (debits) vs returns (credits), optionally scoped to one
    platform. Returns `platforms` (the full label list for the chart's picker chips,
    ordered by total activity) and `data` (one row per month: {month, label, invested,
    returns}) for the selected platform, or all platforms when none is given."""
    q = db.query(Transaction).filter(
        Transaction.data_mode == mode,
        Transaction.is_investment == True,
    )
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    platform_for = _platform_labeler(db)
    labeled = [(platform_for(t.description)[0], t) for t in q.all()]

    # full platform list for the picker chips — independent of the current selection
    totals: collections.Counter = collections.Counter()
    for label, t in labeled:
        totals[label] += t.amount
    platforms = [p for p, _ in totals.most_common()]

    monthly: dict[str, dict[str, float]] = collections.defaultdict(lambda: {"invested": 0.0, "returns": 0.0})
    for label, t in labeled:
        if platform and label != platform:
            continue
        bucket = monthly[t.date.strftime("%Y-%m")]
        if t.transaction_type == "debit":
            bucket["invested"] += t.amount
        elif t.transaction_type == "credit":
            bucket["returns"] += t.amount

    data = []
    for ym in sorted(monthly):
        y, m = ym.split("-")
        data.append({
            "month": ym,
            "label": date(int(y), int(m), 1).strftime("%b %y"),
            "invested": round(monthly[ym]["invested"], 2),
            "returns": round(monthly[ym]["returns"], 2),
        })
    return {"platforms": platforms, "data": data}
