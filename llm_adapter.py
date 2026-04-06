from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from schema_manager import format_schema_text

load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it to use natural language queries.")
    return OpenAI(api_key=api_key)


def _clean_sql_output(content: str) -> str:
    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    if content.lower().startswith("sql"):
        content = content[3:].strip()

    return content


def nl_to_sql(user_input: str, schema: Dict[str, List[str]]) -> str:
    schema_text = format_schema_text(schema)

    prompt = f"""
You are a helpful assistant that writes SQLite SELECT queries.

Schema:
{schema_text}

User question:
{user_input}

Rules:
- Return one valid SQLite SELECT statement.
- Do not include any commentary or markdown.
- Never modify data (no INSERT/UPDATE/DELETE/DDL).
"""

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    return _clean_sql_output(content)
