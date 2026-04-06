import cli


def test_cli_schema_command_prints_schema(monkeypatch, capsys):
    inputs = iter(["schema", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(cli, "build_schema", lambda: {"employees": ["id", "name"]})

    cli.repl()

    output = capsys.readouterr().out
    assert "employees: id, name" in output


def test_cli_sql_command_routes_through_query_service(monkeypatch, capsys):
    inputs = iter(["sql SELECT name FROM employees", "exit"])
    seen = {}

    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    def fake_run_query(sql):
        seen["sql"] = sql
        return [{"name": "Alice"}]

    monkeypatch.setattr(cli, "run_query", fake_run_query)

    cli.repl()

    output = capsys.readouterr().out
    assert seen["sql"] == "SELECT name FROM employees"
    assert "Alice" in output


def test_cli_ask_command_uses_llm_and_prints_generated_sql(monkeypatch, capsys):
    inputs = iter(["ask show all names", "exit"])

    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(cli, "build_schema", lambda: {"employees": ["id", "name"]})
    monkeypatch.setattr(cli, "nl_to_sql", lambda question, schema: "SELECT name FROM employees")
    monkeypatch.setattr(cli, "run_query", lambda sql: [{"name": "Bob"}])

    cli.repl()

    output = capsys.readouterr().out
    assert "Generated SQL -> SELECT name FROM employees" in output
    assert "Bob" in output


def test_cli_handles_validation_error(monkeypatch, capsys):
    inputs = iter(["sql SELECT nope FROM employees", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    def fake_run_query(_sql):
        raise cli.ValidationError("Unknown column: nope")

    monkeypatch.setattr(cli, "run_query", fake_run_query)

    cli.repl()

    output = capsys.readouterr().out
    assert "Validation error: Unknown column: nope" in output
