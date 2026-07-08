from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cash_expense import CashExpense
from app.models.transaction import Transaction
from app.schemas.cash_expense import CashExpenseCreate, CashExpenseOut
from app.utils.cash_expenses import sync_cash_expenses, CASH_SOURCE

router = APIRouter(prefix="/cash-expenses", tags=["cash-expenses"])


@router.get("", response_model=list[CashExpenseOut])
def list_cash_expenses(db: Session = Depends(get_db)):
    return db.query(CashExpense).order_by(CashExpense.name).all()


@router.post("", status_code=201)
def create_cash_expense(body: CashExpenseCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name or body.amount <= 0:
        raise HTTPException(status_code=422, detail="Name and a positive amount are required")
    e = CashExpense(
        name=name, amount=body.amount, day_of_month=body.day_of_month or 1,
        type=(body.type or "Cash").strip(), frequency=body.frequency or "monthly",
        start_date=body.start_date, active=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    generated = sync_cash_expenses(db)   # backfill its debits up to today
    return {"expense": CashExpenseOut.model_validate(e), "generated": generated}


@router.delete("/{expense_id}", status_code=204)
def delete_cash_expense(expense_id: int, db: Session = Depends(get_db)):
    e = db.query(CashExpense).filter(CashExpense.id == expense_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Cash expense not found")
    # remove the debits it generated (source + the expense name identify them)
    db.query(Transaction).filter(
        Transaction.source == CASH_SOURCE, Transaction.description == e.name
    ).delete()
    db.delete(e)
    db.commit()
