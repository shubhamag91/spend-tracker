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
