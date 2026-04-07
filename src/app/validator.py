from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword, Wildcard, Whitespace, Newline, Punctuation


class ValidationError(Exception):
    """Raised when SQL validation fails."""


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "DROP",
    "DELETE",
    "UPDATE",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
}


def _is_identifier(token) -> bool:
    return isinstance(token, Identifier)


def _extract_tables(statement) -> Tuple[Dict[str, str], Set[int]]:
    """
    Extract tables and aliases.
    Returns mapping alias->real table, and ids of identifier tokens representing tables.
    """
    tables: Dict[str, str] = {}
    table_token_ids: Set[int] = set()

    def record_identifier(ident: Identifier):
        real_name = ident.get_real_name()
        alias = ident.get_alias() or real_name
        if real_name:
            tables[alias.lower()] = real_name.lower()
            tables[real_name.lower()] = real_name.lower()
            table_token_ids.add(id(ident))

    in_from = False
    for token in statement.tokens:
        if token.ttype in (Whitespace, Newline, Punctuation):
            continue
        if token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"}:
            in_from = True
            continue
        if in_from:
            if token.ttype is Keyword and token.value.upper() in {"WHERE", "GROUP", "ORDER", "LIMIT", "HAVING"}:
                in_from = False
                continue
            if isinstance(token, IdentifierList):
                for ident in token.get_identifiers():
                    record_identifier(ident)
                continue
            if isinstance(token, Identifier):
                record_identifier(token)
                continue
            # other tokens (e.g., subqueries) are ignored for now

    return tables, table_token_ids


def _identifier_to_column(identifier: Identifier) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Return (table_or_alias, column_name, is_wildcard).
    """
    if identifier.is_wildcard():
        return identifier.get_parent_name(), "*", True
    return identifier.get_parent_name(), identifier.get_real_name(), False


def _collect_columns(token, skip_ids: Set[int]) -> Iterable[Tuple[Optional[str], Optional[str], bool]]:
    """
    Walk tokens collecting column references, skipping identifiers known to be tables.
    """
    if isinstance(token, IdentifierList):
        for ident in token.get_identifiers():
            yield from _collect_columns(ident, skip_ids)
    elif isinstance(token, Identifier):
        if id(token) in skip_ids:
            return
        yield _identifier_to_column(token)
        for child in token.tokens:
            yield from _collect_columns(child, skip_ids)
    elif token.ttype is Wildcard:
        yield (None, "*", True)
    elif getattr(token, "is_group", False):
        for child in token.tokens:
            yield from _collect_columns(child, skip_ids)


def _ensure_no_forbidden_keywords(statement):
    for token in statement.tokens:
        if token.ttype is Keyword and token.value.upper() in FORBIDDEN_KEYWORDS:
            raise ValidationError(f"Forbidden keyword detected: {token.value}")


def validate_sql(sql: str, schema: Dict[str, List[str]]) -> bool:
    """
    Validate generated SQL is a safe SELECT over known schema.
    - Only one statement
    - Only SELECT
    - Tables exist
    - Columns exist
    """
    sql = sql.strip()
    if not sql:
        raise ValidationError("Empty query.")

    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        raise ValidationError("Only a single statement is allowed.")

    statement = parsed[0]

    if statement.get_type() != "SELECT":
        raise ValidationError("Only SELECT statements are allowed.")

    _ensure_no_forbidden_keywords(statement)

    tables, table_token_ids = _extract_tables(statement)
    if not tables:
        raise ValidationError("Query must reference at least one table.")

    schema_lower = {tbl.lower(): {c.lower() for c in cols} for tbl, cols in schema.items()}

    for alias, real in tables.items():
        if real not in schema_lower:
            raise ValidationError(f"Unknown table: {real}")

    columns = list(_collect_columns(statement, table_token_ids))
    if not columns:
        raise ValidationError("No columns found in query.")

    for table_alias, col, is_wildcard in columns:
        if is_wildcard:
            # SELECT * is allowed if table exists (already checked)
            continue
        if not col:
            raise ValidationError("Invalid column reference.")

        if table_alias:
            table_alias = table_alias.lower()
            table = tables.get(table_alias)
            if not table:
                raise ValidationError(f"Unknown table alias: {table_alias}")
            if col.lower() not in schema_lower.get(table, set()):
                raise ValidationError(f"Unknown column '{col}' on table '{table}'.")
        else:
            # unqualified column: must belong to exactly one table to avoid ambiguity
            matches = [tbl for tbl, cols in schema_lower.items() if col.lower() in cols]
            if not matches:
                raise ValidationError(f"Unknown column: {col}")
            if len(matches) > 1:
                raise ValidationError(f"Ambiguous column '{col}'. Qualify with table name.")

    return True
