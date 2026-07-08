"""Tiny idempotent schema migrations for SQLite.

The project creates tables with Base.metadata.create_all, which makes new tables
(like `accounts`) but never ALTERs an existing table to add a column. This module
fills that gap for additive column changes so an already-populated DB upgrades in
place without dropping data. Safe to run on every startup.
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# (table, column, column DDL) — additive only.
_ADDITIVE_COLUMNS = [
    ("transactions", "account_id", "INTEGER REFERENCES accounts(id)"),
    ("transactions", "bucket", "TEXT"),
    ("subscription_rules", "frequency", "TEXT NOT NULL DEFAULT 'monthly'"),
    ("subscription_rules", "min_amount", "REAL"),
    ("subscription_rules", "monthly_amount", "REAL"),
    ("investment_rules", "label", "TEXT"),
]


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in _ADDITIVE_COLUMNS:
            if table not in existing_tables:
                continue  # create_all will build it fresh with the column already present
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column not in cols:
                logger.info("migration: adding %s.%s", table, column)
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
    _drop_subscription_keyword_unique(engine)


def _drop_subscription_keyword_unique(engine: Engine) -> None:
    """SQLite can't ALTER away a UNIQUE constraint, so rebuild `subscription_rules`
    without the keyword-unique once (multiple bills can share a merchant string,
    disambiguated by min_amount). Idempotent — only runs while the constraint exists.
    """
    insp = inspect(engine)
    if "subscription_rules" not in insp.get_table_names():
        return
    has_unique = any(u.get("column_names") == ["keyword"] for u in insp.get_unique_constraints("subscription_rules")) or \
        any(i.get("unique") and i.get("column_names") == ["keyword"] for i in insp.get_indexes("subscription_rules"))
    if not has_unique:
        return

    from app.models.subscription_rule import SubscriptionRule
    cols = [c.name for c in SubscriptionRule.__table__.columns]
    collist = ", ".join(cols)
    with engine.begin() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(f"SELECT {collist} FROM subscription_rules"))]
        conn.execute(text("DROP TABLE subscription_rules"))
    SubscriptionRule.__table__.create(bind=engine)  # recreate from the model (no unique)
    if rows:
        placeholders = ", ".join(f":{c}" for c in cols)
        with engine.begin() as conn:
            conn.execute(text(f"INSERT INTO subscription_rules ({collist}) VALUES ({placeholders})"), rows)
    logger.info("migration: rebuilt subscription_rules without keyword-unique (%d rows kept)", len(rows))
