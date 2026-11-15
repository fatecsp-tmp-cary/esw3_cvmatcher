import pytest
from sqlalchemy import select

from src.extraction.contracts import SpanEvidence
from src.extraction.persistence import persist_requirements, seed_taxonomy
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.skill import JobRequirement, JobSkill, Skill


def test_classified_generation_preserves_canonical_content_and_replaces_associations(db_session):
    session = db_session
    source = JobSource(name="classified-fixture", type="api", polling_mode="INCREMENTAL")
    session.add(source)
    session.flush()
    job = Job(
        source_id=source.id,
        platform="fixture",
        source_job_id="classified",
        title="Developer",
        status=JobStatus.ACTIVE,
        content_hash="unchanged",
        skills=[],
    )
    session.add(job)
    session.flush()
    text = "Required: Python\nPreferred: PostgreSQL\nOptional: Docker\nUnknown: SQL"
    evidence = [
        SpanEvidence(text.rindex(name), text.rindex(name) + len(name), "skill", 0.9).serialize(text)
        for name in ["Python", "PostgreSQL", "Docker", "SQL"]
    ]
    persist_requirements(session, job, evidence, text)
    rows = session.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)).all()
    assert {(row.text, row.requirement_class.value) for row in rows} == {
        ("Python", "REQUIRED"),
        ("PostgreSQL", "PREFERRED"),
        ("Docker", "NICE_TO_HAVE"),
    }
    assert evidence[-1]["requirement_class"] is None
    assert job.content_hash == "unchanged" and job.skills == []
    before = session.scalars(select(Skill.id).order_by(Skill.id)).all()
    seed_taxonomy(session)
    assert session.scalars(select(Skill.id).order_by(Skill.id)).all() == before
    text = "Preferred: JS"
    evidence = [SpanEvidence(11, 13, "skill", 0.9).serialize(text)]
    persist_requirements(session, job, evidence, text)
    assert evidence[0]["canonical_skill"] == "JavaScript"
    assert session.scalars(
        select(JobRequirement.text).where(JobRequirement.job_id == job.id)
    ).all() == ["JS"]
    assert session.scalars(
        select(Skill.canonical_name).join(JobSkill).where(JobSkill.job_id == job.id)
    ).all() == ["JavaScript"]


def test_conflicting_requirement_strengths_keep_strongest_with_unsafe_flag(db_session):
    session = db_session
    source = JobSource(name="conflict-fixture", type="api", polling_mode="INCREMENTAL")
    session.add(source)
    session.flush()
    job = Job(source_id=source.id, platform="fixture", source_job_id="conflict", title="Role")
    session.add(job)
    session.flush()
    text = "Required: Python\nOptional: Python"
    starts = [text.index("Python"), text.rindex("Python")]
    evidence = [SpanEvidence(start, start + 6, "skill", 0.9).serialize(text) for start in starts]
    persist_requirements(session, job, evidence, text)
    assert all(item["conflicting"] and not item["exclusion_safe"] for item in evidence)
    assert [item["requirement_class"] for item in evidence] == ["REQUIRED", "NICE_TO_HAVE"]
    rows = session.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)).all()
    assert len(rows) == 1 and rows[0].requirement_class.value == "REQUIRED"


def test_approximate_evidence_is_score_only_and_negation_retains_no_association(db_session):
    session = db_session
    source = JobSource(name="approximate-fixture", type="api", polling_mode="INCREMENTAL")
    session.add(source)
    session.flush()
    job = Job(source_id=source.id, platform="fixture", source_job_id="approximate", title="Role")
    session.add(job)
    session.flush()
    text = "Pyhton required. Java is not required."
    evidence = [
        SpanEvidence(text.index(name), text.index(name) + len(name), "skill", 0.9).serialize(text)
        for name in ("Pyhton", "Java")
    ]
    persist_requirements(session, job, evidence, text)
    (row,) = session.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)).all()
    assert row.text == "Pyhton" and row.skill_id is None
    assert evidence[0]["approximate_match"] and not evidence[0]["exclusion_safe"]
    assert evidence[1]["requirement_class"] is None and evidence[1]["negated"]
    assert session.scalars(
        select(Skill.canonical_name).join(JobSkill).where(JobSkill.job_id == job.id)
    ).all() == ["Python"]
    seed = session.scalar(select(Skill).where(Skill.canonical_name == "Python"))
    assert "pyhton" not in seed.aliases


@pytest.mark.parametrize(
    "text",
    [
        "Python required, but not Java.",
        "Python obrigatório, mas não Java.",
        "Requirements:\nPython required\nBenefits: health insurance\nJava required.",
        "Requisitos:\nPython obrigatório\nBenefícios: plano de saúde\nJava obrigatório.",
    ],
)
def test_negation_and_inline_background_do_not_persist_positive_associations(db_session, text):
    source = JobSource(name="local-context-review", type="api", polling_mode="INCREMENTAL")
    db_session.add(source)
    db_session.flush()
    job = Job(source_id=source.id, platform="fixture", source_job_id="context", title="Role")
    db_session.add(job)
    db_session.flush()
    raw = []
    persist_requirements(db_session, job, raw, text)
    assert db_session.scalars(
        select(JobRequirement.text).where(JobRequirement.job_id == job.id)
    ).all() == ["Python"]
    assert db_session.scalars(
        select(Skill.canonical_name).join(JobSkill).where(JobSkill.job_id == job.id)
    ).all() == ["Python"]
    java = next(row for row in raw if text[row["start"] : row["end"]] == "Java")
    assert java["requirement_class"] is None
    assert not java["exclusion_safe"]
