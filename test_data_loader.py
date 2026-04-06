import tempfile
from pathlib import Path

import pandas as pd
import pytest

from data_loader import load_csv
from db import get_connection
from schema_manager import get_table_schema


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    log_path = tmp_path / "error_log.txt"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.chdir(tmp_path)
    yield log_path


def _write_csv(df: pd.DataFrame) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_csv:
        df.to_csv(tmp_csv.name, index=False)
        return tmp_csv.name


def test_new_table_gets_auto_increment_primary_key():
    csv_path = _write_csv(pd.DataFrame({"name": ["Alice"], "age": [30]}))

    load_csv(csv_path, "people")
    schema = get_table_schema("people")

    assert schema[0]["name"] == "id"
    assert schema[0]["type"].upper() == "INTEGER"
    assert [column["name"] for column in schema[1:]] == ["name", "age"]


def test_matching_schema_appends_rows():
    csv_path_1 = _write_csv(pd.DataFrame({"name": ["Alice"], "age": [30]}))
    csv_path_2 = _write_csv(pd.DataFrame({"name": ["Bob"], "age": [25]}))

    load_csv(csv_path_1, "people")
    load_csv(csv_path_2, "people")

    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name, age FROM people ORDER BY id").fetchall()
    finally:
        conn.close()

    assert [row["name"] for row in rows] == ["Alice", "Bob"]
    assert [row["id"] for row in rows] == [1, 2]


def test_schema_conflict_logs_error(temp_db):
    csv_path_1 = _write_csv(pd.DataFrame({"name": ["Alice"], "age": [30]}))
    csv_path_2 = _write_csv(pd.DataFrame({"name": ["Bob"], "salary": [100000.0]}))

    load_csv(csv_path_1, "people")

    with pytest.raises(ValueError):
        load_csv(csv_path_2, "people")

    assert temp_db.exists()
    assert "Schema conflict for table 'people'" in temp_db.read_text()
