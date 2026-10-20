"""
sqlite3 connection handling.

Uses plain sqlite3 (no ORM), one connection per request via Flask's
application context (`g`), with parameterized queries everywhere to avoid
SQL injection. Foreign keys and WAL mode are enabled for durability and
better concurrent read performance.
"""

import sqlite3
from pathlib import Path

from flask import current_app, g


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = _connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables if they don't exist yet. Called once at app startup."""
    schema_path = Path(__file__).parent / "schema.sql"
    with app.app_context():
        db = _connect(app.config["DB_PATH"])
        with open(schema_path, "r") as f:
            db.executescript(f.read())
        db.commit()
        db.close()

    app.teardown_appcontext(close_db)
