# EC530 Data Systems with LLM

Safe, modular SQLite querying with LLM-generated SQL that is always validated before execution.

## Quickstart

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py
```

### CLI commands
- `load <csv_path> <table_name>` — ingest a CSV (schema inferred) into SQLite.
- `schema` — list tables and columns known to the system.
- `sql <SELECT ...>` — run a raw SELECT (validated first).
- `ask <natural language question>` — LLM to SQL to validate to execute.
- `exit` — quit.

## Architecture

User to CLI to Query Service to (LLM Adapter) to Validator to SQLite

- **CLI (`cli.py`)**: interactive loop; routes all actions through the Query Service.
- **Query Service (`query_service.py`)**: builds schema map, calls validator, executes safe SQL.
- **LLM Adapter (`llm_adapter.py`)**: turns natural language into SQL using OpenAI; never executes SQL.
- **SQL Validator (`validator.py`)**: structural checks — single SELECT only, known tables, known columns, no forbidden keywords; rejects ambiguous columns.
- **Schema Manager (`schema_manager.py`)**: enumerates tables/columns and formats schema for prompts.
- **Data Loader (`data_loader.py`)**: infers column types from CSV, creates or appends to matching tables.
- **DB (`db.py`)**: SQLite connection helper honoring `DB_PATH` env var (used by tests).
- **Note:** ingestion is fully manual (`executemany`) and never uses `pandas.DataFrame.to_sql()` to comply with assignment rules.

### Defensive design
- LLM output is treated as untrusted input.
- Validator runs before any execution.
- Only SELECT is allowed; DDL/DML keywords are blocked.
- Unknown/ambiguous columns or tables raise `ValidationError`.

## Testing

```
python -m pytest
```

What’s covered:
- Validator accepts good queries and rejects DML, unknown tables/columns, ambiguity, multi-statements, and bad WHERE references.
- End-to-end flow: load CSV to query to expected rows.
- Demonstration that a bad LLM-style SQL (`SELECT title FROM employees`) is caught by the validator.
