from types import SimpleNamespace

import pytest

import llm_adapter


class _FakeClient:
    def __init__(self, content: str):
        self._content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.last_kwargs = None

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content)
                )
            ]
        )


def test_clean_sql_output_removes_markdown_fence():
    content = "```sql\nSELECT name FROM employees\n```"
    assert llm_adapter._clean_sql_output(content) == "SELECT name FROM employees"


def test_nl_to_sql_builds_prompt_and_returns_clean_sql(monkeypatch):
    fake_client = _FakeClient("```sql\nSELECT name FROM employees\n```")
    monkeypatch.setattr(llm_adapter, "_get_client", lambda: fake_client)

    sql = llm_adapter.nl_to_sql(
        "show all employee names",
        {"employees": ["id", "name", "department"]},
    )

    assert sql == "SELECT name FROM employees"
    assert fake_client.last_kwargs["model"] == "gpt-4o-mini"
    prompt = fake_client.last_kwargs["messages"][0]["content"]
    assert "employees: id, name, department" in prompt
    assert "show all employee names" in prompt


def test_get_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        llm_adapter._get_client()
