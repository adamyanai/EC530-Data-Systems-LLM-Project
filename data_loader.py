from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from db import get_connection
from schema_manager import get_table_schema

VALID_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ensure_valid_identifier(name: str, kind: str) -> str:
    if not VALID_NAME.match(name):
        raise ValueError(f"Invalid {kind} name '{name}'. Use letters, numbers, and underscores only.")
    return name


def _infer_sql_type(series: pd.Series) -> str:
    """Infer a SQLite column type from a pandas Series."""
    if pd.api.types.is_integer_dtype(series.dropna()):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series.dropna()):
        return "REAL"
    if pd.api.types.is_bool_dtype(series.dropna()):
        return "INTEGER"
    return "TEXT"


def _build_schema(df: pd.DataFrame) -> List[Tuple[str, str]]:
    return [(col, _infer_sql_type(df[col])) for col in df.columns]


def _log_schema_conflict(table_name: str, existing, incoming) -> None:
    with open("error_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(
            f"Schema conflict for table '{table_name}'. "
            f"Existing schema={existing} Incoming schema={incoming}\n"
        )


def _schemas_match(existing: List[Dict[str, str]], incoming: List[Tuple[str, str]]) -> bool:
    """Compare existing schema (list of dicts) with incoming schema tuples."""
    managed_columns = {"id"}
    existing_user_columns = [
        col for col in existing if col["name"].lower() not in managed_columns
    ]

    if len(existing_user_columns) != len(incoming):
        return False

    existing_map = {
        col["name"].lower(): col["type"].upper() for col in existing_user_columns
    }
    for name, col_type in incoming:
        if existing_map.get(name.lower()) != col_type.upper():
            return False
    return True


def load_csv(file_path: str, table_name: str) -> Dict[str, str]:
    """
    Load a CSV into SQLite.
    - Infers column types.
    - Creates table if missing.
    - Appends rows if schema matches, otherwise raises.
    Returns the schema used.
    """
    table_name = _ensure_valid_identifier(table_name, "table")
    df = pd.read_csv(file_path)
    if df.empty:
        raise ValueError("CSV file is empty.")

    cleaned_columns = []
    for col in df.columns:
        clean = _ensure_valid_identifier(str(col).strip(), "column")
        cleaned_columns.append(clean)

    if len(cleaned_columns) != len(set(name.lower() for name in cleaned_columns)):
        raise ValueError("CSV contains duplicate column names after normalization.")

    df.columns = cleaned_columns

    incoming_schema = _build_schema(df)

    conn = get_connection()
    try:
        existing_schema = get_table_schema(table_name, conn)
        if existing_schema:
            if not _schemas_match(existing_schema, incoming_schema):
                _log_schema_conflict(table_name, existing_schema, incoming_schema)
                raise ValueError(
                    f"Table '{table_name}' already exists with a different schema. "
                    "Choose a new table name or adjust your CSV."
                )
        else:
            cols_sql = ", ".join(f"{name} {col_type}" for name, col_type in incoming_schema)
            conn.execute(
                f"CREATE TABLE {table_name} ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                f"{cols_sql})"
            )

        placeholders = ", ".join(["?"] * len(df.columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({placeholders})"

        rows = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False)]
        conn.executemany(insert_sql, rows)
        conn.commit()
    finally:
        conn.close()

    return dict(incoming_schema)
