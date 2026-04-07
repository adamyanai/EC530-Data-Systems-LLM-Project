import os
import sqlite3
from typing import Optional


def _db_path() -> str:
    """Resolve the active database path (env overridable)."""
    return os.getenv("DB_PATH", "data.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a SQLite connection with row factory set for named access."""
    conn = sqlite3.connect(db_path or _db_path())
    conn.row_factory = sqlite3.Row
    return conn
