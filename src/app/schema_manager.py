from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.db import get_connection

VALID_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ensure_valid_identifier(name: str) -> str:
    if not VALID_NAME.match(name):
        raise ValueError(f"Invalid identifier '{name}'.")
    return name


def get_tables(conn=None) -> List[str]:
    owned = conn is None
    conn = conn or get_connection()
    res = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    if owned:
        conn.close()
    return [r[0] for r in res]


def get_table_schema(table: str, conn=None) -> List[Dict[str, str]]:
    """Return list of columns with names and types for a single table."""
    table = _ensure_valid_identifier(table)
    owned = conn is None
    conn = conn or get_connection()
    res = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if owned:
        conn.close()
    return [{"name": r["name"], "type": r["type"]} for r in res]


def build_schema_map(conn=None) -> Dict[str, List[str]]:
    """
    Return a schema mapping: table -> list of column names.
    Column names are lowercased for easier comparison.
    """
    owned = conn is None
    conn = conn or get_connection()
    schema = {}
    for table in get_tables(conn):
        schema[table] = [col["name"].lower() for col in get_table_schema(table, conn)]
    if owned:
        conn.close()
    return schema


def format_schema_text(schema: Dict[str, List[str]]) -> str:
    """Nicely format schema for prompts and display."""
    lines = []
    for table, cols in schema.items():
        cols_str = ", ".join(cols)
        lines.append(f"{table}: {cols_str}")
    return "\n".join(lines)
