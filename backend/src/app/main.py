import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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


# ── Single-server mode ──────────────────────────────────────────────────────────
# Serve the built frontend (frontend/dist) from this same FastAPI process, so the
# whole app runs on one port — no separate Node server needed. This block is a
# no-op until you build the frontend (`cd frontend && npm run build`); during UI
# development you can still run the Vite dev server for hot-reload instead.
_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    _ASSETS = _FRONTEND_DIST / "assets"
    if _ASSETS.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    _DIST_ROOT = _FRONTEND_DIST.resolve()

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # static file if it exists (favicon, etc.), else index.html for SPA routes.
        # API routes are registered above, so they take precedence over this catch-all.
        # Resolve and contain the path inside dist — `full_path` can carry `../` (and
        # %2f-encoded slashes), so without this guard the catch-all would serve any
        # file on disk (e.g. the SQLite DB). See path-traversal fix.
        candidate = (_FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_DIST_ROOT):
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")

    logger.info("single-server mode: serving frontend from %s", _FRONTEND_DIST)
