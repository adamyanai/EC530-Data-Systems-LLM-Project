from __future__ import annotations

from typing import List

from app.data_loader import load_csv
from app.llm_adapter import nl_to_sql
from app.query_service import build_schema, run_query
from app.validator import ValidationError


def _print_rows(rows: List) -> None:
    if not rows:
        print("No rows returned.")
        return
    for row in rows:
        if hasattr(row, "keys"):
            print({k: row[k] for k in row.keys()})
        else:
            print(row)


def repl():
    print("Type 'help' for commands. 'exit' to quit.")
    while True:
        cmd = input(">> ").strip()
        if not cmd:
            continue
        if cmd in {"exit", "quit"}:
            break
        if cmd == "help":
            print(
                "Commands:\n"
                "  load <csv_path> <table_name>  - load CSV into database\n"
                "  schema                        - show current tables/columns\n"
                "  sql <SELECT ...>              - run raw SQL (validated)\n"
                "  ask <natural language>        - LLM to SQL to execute\n"
                "  exit                          - quit\n"
            )
            continue
        if cmd == "schema":
            schema = build_schema()
            for table, cols in schema.items():
                print(f"{table}: {', '.join(cols)}")
            continue

        try:
            if cmd.startswith("load "):
                _, file, table = cmd.split(maxsplit=2)
                schema = load_csv(file, table)
                print(f"Loaded '{file}' into table '{table}'. Schema: {schema}")
                continue

            if cmd.startswith("sql "):
                sql = cmd[len("sql ") :]
            elif cmd.startswith("ask "):
                question = cmd[len("ask ") :]
                sql = nl_to_sql(question, build_schema())
                print(f"Generated SQL -> {sql}")
            else:
                sql = nl_to_sql(cmd, build_schema())
                print(f"Generated SQL -> {sql}")

            rows = run_query(sql)
            _print_rows(rows)
        except ValidationError as err:
            print(f"Validation error: {err}")
        except Exception as err:
            print(f"Error: {err}")


if __name__ == "__main__":
    repl()
