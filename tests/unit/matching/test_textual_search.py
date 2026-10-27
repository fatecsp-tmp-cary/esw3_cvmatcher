import pytest
from sqlalchemy.dialects import postgresql

from src.matching.textual import search_active_jobs


class NoExecuteSession:
    def execute(self, statement):
        self.statement = statement
        return self

    def all(self):
        return []


def test_search_uses_portuguese_fts_and_active_jobs():
    session = NoExecuteSession()

    assert search_active_jobs(session, "engenheira de dados") == []

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "'portuguese'::regconfig" in sql
    assert "websearch_to_tsquery" in sql
    assert "job_requirements" in sql
    assert "jobs.status =" in sql
    assert "ORDER BY" in sql


@pytest.mark.parametrize("query", [None, 42])
def test_search_requires_text_query(query):
    with pytest.raises(TypeError, match="query must be text"):
        search_active_jobs(NoExecuteSession(), query)


@pytest.mark.parametrize("limit", [0, 501, 1.5, True])
def test_search_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit must be between"):
        search_active_jobs(NoExecuteSession(), "python", limit=limit)


def test_blank_query_returns_without_database_call():
    class FailingSession:
        def execute(self, statement):
            raise AssertionError("blank query must not hit the database")

    assert search_active_jobs(FailingSession(), "   ") == []
