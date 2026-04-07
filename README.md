# EC530 Data Systems with LLM Interfaces

This project implements a modular SQLite-based data system that loads structured CSV data, exposes a command-line interface, translates natural-language questions into SQL with an LLM, validates the generated SQL, and only then executes safe read-only queries.

## System overview

The project is split into independent components so each part can be tested in isolation:

- `src/app/cli.py`: command-line interface. It never talks to SQLite directly.
- `src/app/query_service.py`: service layer that coordinates schema lookup, SQL validation, and execution.
- `src/app/llm_adapter.py`: converts natural-language questions into SQLite `SELECT` statements.
- `src/app/validator.py`: validates SQL structure and schema references before execution.
- `src/app/schema_manager.py`: discovers tables and columns and formats schema context for the LLM.
- `src/app/data_loader.py`: reads CSV files, infers schema, creates tables, and appends compatible rows.
- `src/app/db.py`: SQLite connection helper.
- `tests/`: isolated pytest suite for validators, loader, query flow, CLI, and LLM adapter.

## Architecture

Primary query flow: CLI -> Query Service -> LLM Adapter -> Validator -> SQLite

Data ingestion flow: CLI -> Data Loader -> Schema Manager -> SQLite

```mermaid
flowchart LR
    CLI[CLI Interface]
    QS[Query Service]
    LLM[LLM Adapter]
    VAL[SQL Validator]
    SM[Schema Manager]
    DL[CSV Loader]
    DB[(SQLite)]

    CLI --> QS
    CLI --> DL
    DL --> SM
    DL --> DB
    QS --> SM
    QS --> LLM
    QS --> VAL
    VAL --> DB
```

## Design choices

- The CLI is intentionally thin. It handles input and display only.
- The query service is the single gateway for query execution.
- LLM output is treated as untrusted input and is always revalidated.
- The validator operates on query structure and schema references rather than trying to be a full SQL parser.
- CSV ingestion is implemented manually with `executemany`; it does not use `pandas.DataFrame.to_sql()`.
- New tables include `id INTEGER PRIMARY KEY AUTOINCREMENT` as required.
- Schema mismatches during ingestion are logged to `error_log.txt`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=src python3 -m app.cli
```

If you want to use the LLM path, set `OPENAI_API_KEY` in `.env`.

## CLI usage

- `load <csv_path> <table_name>` loads a CSV into SQLite.
- `schema` prints the known tables and columns.
- `sql <SELECT ...>` runs validated SQL directly.
- `ask <natural language question>` sends the prompt to the LLM adapter, validates the returned SQL, and executes it.
- `exit` quits the application.

## Testing

Run the test suite with:

```bash
pytest -q
```

Current tests cover:

- validator acceptance and rejection behavior
- unknown tables and columns
- ambiguous column references
- end-to-end CSV load and query execution
- append behavior for matching schemas
- required auto-increment primary key creation
- schema conflict logging
- CLI behavior with mocked query-service and LLM dependencies
- LLM adapter prompt/output handling with a mocked OpenAI client
- a case where bad LLM-style SQL is rejected by the validator

## CI pipeline

GitHub Actions runs `pytest -q` on every push and pull request using `.github/workflows/ci.yml`.

## AI usage

AI was used as a development companion for design refinement and validator implementation support. Final behavior is defined by the project code and tests, not by the LLM. In particular:

- the LLM adapter only generates SQL text
- the validator defines allowed behavior
- unit tests are used to confirm and refine the implementation

## Validator refinement

One required part of the assignment was showing that the system remains correct when the LLM is wrong.

The concrete failure case used in this project is:

- natural-language request targets the `employees` table
- LLM-generated SQL returns `SELECT title FROM employees`
- the schema does not contain a `title` column

This behavior is captured in the test suite, where the query service rejects that SQL before execution. The relevant test is [test_query_service.py](/EC530-Data-Systems-LLM-Project/tests/test_query_service.py#L34).

The refinement story is:

- initial risk: an LLM can hallucinate a column that does not exist
- test expectation: unknown columns must raise `ValidationError`
- implementation refinement: the validator was tightened so it checks column references against the live schema, including columns used in `SELECT` and `WHERE` clauses
- final behavior: incorrect LLM SQL is rejected safely and never reaches SQLite execution
