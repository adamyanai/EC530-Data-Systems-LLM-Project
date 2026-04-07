from __future__ import annotations

from typing import Any, Dict, List

from app.db import get_connection
from app.schema_manager import build_schema_map
from app.validator import ValidationError, validate_sql


def build_schema() -> Dict[str, List[str]]:
    """Return the current schema map (table -> columns)."""
    return build_schema_map()


def execute_sql(sql: str) -> List[Any]:
    """Execute validated SQL and return rows."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def run_query(sql: str) -> List[Any]:
    """
    Validate a SQL query against the current schema and execute it.
    Raises ValidationError for unsafe SQL.
    """
    schema = build_schema()
    validate_sql(sql, schema)
    return execute_sql(sql)
