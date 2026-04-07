import pytest

from app.validator import ValidationError, validate_sql


def test_valid_query():
    schema = {"users": ["id", "name"]}
    assert validate_sql("SELECT name FROM users", schema)


def test_reject_non_select():
    schema = {"users": ["id", "name"]}
    with pytest.raises(ValidationError):
        validate_sql("UPDATE users SET name='x'", schema)


def test_unknown_table():
    schema = {"users": ["id", "name"]}
    with pytest.raises(ValidationError):
        validate_sql("SELECT name FROM employees", schema)


def test_unknown_column_in_select():
    schema = {"users": ["id", "name"]}
    with pytest.raises(ValidationError):
        validate_sql("SELECT age FROM users", schema)


def test_unknown_column_in_where():
    schema = {"users": ["id", "name"]}
    with pytest.raises(ValidationError):
        validate_sql("SELECT name FROM users WHERE age > 30", schema)


def test_ambiguous_column():
    schema = {"users": ["id", "name"], "orders": ["id", "total"]}
    with pytest.raises(ValidationError):
        validate_sql("SELECT id FROM users JOIN orders ON users.id = orders.id", schema)


def test_join_with_alias():
    schema = {"users": ["id", "name"], "orders": ["id", "user_id"]}
    assert validate_sql(
        "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id", schema
    )


def test_forbidden_keyword_in_comment_like():
    schema = {"users": ["id", "name"]}
    with pytest.raises(ValidationError):
        validate_sql("SELECT * FROM users; DROP TABLE users;", schema)
