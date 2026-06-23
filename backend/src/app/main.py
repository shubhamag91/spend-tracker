import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, SessionLocal, Base
from app.models import Account, Category, InvestmentRule, Transaction, IngestLog  # noqa: F401 — ensures models are registered
from app.migrations import run_migrations
from app.api import accounts, categories, transactions, analytics, uploads, demo, investments, subscriptions
from app.categorization.rules import DEFAULT_CATEGORIES
from app.watcher.file_watcher import start_watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _seed_categories(db):
    for cat_data in DEFAULT_CATEGORIES:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            cat = Category(name=cat_data["name"], color=cat_data["color"])
            cat.set_keywords(cat_data["keywords"])
            db.add(cat)
    db.commit()


def _seed_subscription_rules(db):
    from app.models import SubscriptionRule
    from app.subscriptions.defaults import DEFAULT_SUBSCRIPTION_RULES
    # Seed only when empty, so user deletions of defaults aren't resurrected.
    if db.query(SubscriptionRule).first():
        return
    for name, keyword, type_ in DEFAULT_SUBSCRIPTION_RULES:
        db.add(SubscriptionRule(name=name, keyword=keyword, type=type_))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        _seed_categories(db)
        _seed_subscription_rules(db)
    finally:
        db.close()
    start_watcher(settings.watched_folder)
    yield


app = FastAPI(title="Spend Tracker API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router, prefix="/api")
app.include_router(investments.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
