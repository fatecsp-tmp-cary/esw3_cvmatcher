import pytest
from sqlalchemy import true
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

    assert search_active_jobs(session, "engenheira de dados", readiness=true()) == []

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "'pg_catalog.portuguese'::regconfig" in sql
    assert "plainto_tsquery" in sql
    assert "setweight" in sql
    assert "concat_ws" not in sql
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


def test_legacy_readiness_defaults_closed_on_both_paths():
    session = NoExecuteSession()
    assert search_active_jobs(session, "Python") == []
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert sql.count("WHERE false") == 2


def test_legacy_export_and_no_query_length_cap():
    from src.matching import TextualMatch
    from src.matching import search_active_jobs as exported_search

    assert exported_search is search_active_jobs
    assert TextualMatch.__dataclass_params__.frozen
    session = NoExecuteSession()
    query = "Python " * 1000
    assert search_active_jobs(session, query, readiness=true()) == []
    compiled = session.statement.compile(dialect=postgresql.dialect())
    assert query in compiled.params.values()
    assert query not in str(compiled)


def test_legacy_result_preserves_raw_rank():
    job = object()

    class ResultSession:
        def execute(self, statement):
            self.statement = statement
            return self

        def all(self):
            return [(job, 2.5)]

    result = search_active_jobs(ResultSession(), "Python", readiness=true())
    assert result[0].job is job
    assert result[0].score == 2.5
