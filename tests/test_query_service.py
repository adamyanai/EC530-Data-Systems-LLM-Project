import tempfile

import pandas as pd
import pytest

from app.data_loader import load_csv
from app.query_service import build_schema, run_query
from app.validator import ValidationError


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        monkeypatch.setenv("DB_PATH", tmp.name)
        yield


def test_load_and_query_round_trip():
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_csv:
        df.to_csv(tmp_csv.name, index=False)
        csv_path = tmp_csv.name

    load_csv(csv_path, "people")
    schema = build_schema()
    assert "people" in schema
    assert set(schema["people"]) == {"id", "name", "age"}

    rows = run_query("SELECT name FROM people WHERE age > 26")
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"


def test_validator_catches_bad_llm_sql():
    df = pd.DataFrame({"name": ["A"], "department": ["Eng"]})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_csv:
        df.to_csv(tmp_csv.name, index=False)
        csv_path = tmp_csv.name

    load_csv(csv_path, "employees")

    bad_sql = "SELECT title FROM employees"
    with pytest.raises(ValidationError):
        run_query(bad_sql)
