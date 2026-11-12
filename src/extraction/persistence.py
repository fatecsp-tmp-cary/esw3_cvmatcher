"""Versioned project taxonomy and classified associations outside canonical Job."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.extraction.classification import annotate_spans
from src.extraction.taxonomy import _ALIASES
from src.persistence.job.skill import JobRequirement, JobSkill, Skill

SEED_VERSION = "project-explicit-aliases-v1"
SEED_PROVENANCE = "Project-maintained explicit aliases in src/extraction/taxonomy.py"


def seed_taxonomy(session):
    """Idempotent flat roots: no inferred categories/parent relationships."""
    names = sorted(set(_ALIASES.values()))
    for name in names:
        aliases = sorted(alias for alias, canonical in _ALIASES.items() if canonical == name)
        # Preserve independently curated parent/category values. The explicit
        # project seed owns its canonical names and additive aliases only.
        session.execute(
            insert(Skill)
            .values(canonical_name=name, aliases=aliases, category="technology")
            .on_conflict_do_nothing(index_elements=[Skill.canonical_name])
        )
        skill = session.scalar(select(Skill).where(Skill.canonical_name == name).with_for_update())
        skill.aliases = sorted(set(skill.aliases or []) | set(aliases))
        if skill.category is None:
            skill.category = "technology"
    session.flush()


def persist_requirements(session, job, evidence, text):
    """Replace one current extraction generation atomically with claim completion."""
    seed_taxonomy(session)
    session.execute(delete(JobRequirement).where(JobRequirement.job_id == job.id))
    session.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    skills = {s.canonical_name: s.id for s in session.scalars(select(Skill))}
    annotate_spans(text, evidence)
    associated = set()
    seen = set()
    for item in evidence:
        value = text[item["start"] : item["end"]]
        name = item.get("canonical_skill")
        concept = name or value.casefold().strip()
        strength = item["requirement_class"]
        if name:
            item["canonical_skill"] = name
            # Negated/uncertain occurrences remain spans, not positive skills.
            if strength is not None and skills[name] not in associated:
                session.add(JobSkill(job_id=job.id, skill_id=skills[name]))
                associated.add(skills[name])
        if strength is not None and (concept, strength) not in seen:
            session.add(
                JobRequirement(
                    job_id=job.id,
                    text=value,
                    requirement_class=strength,
                    skill_id=skills.get(name),
                )
            )
            seen.add((concept, strength))
    session.flush()
