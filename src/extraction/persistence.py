"""Versioned project taxonomy and classified associations outside canonical Job."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from src.extraction.classification import annotate_spans
from src.extraction.taxonomy import _ALIASES, CATEGORIES, PARENTS, VERSION
from src.persistence.job.skill import JobRequirement, JobSkill, Skill

SEED_VERSION = VERSION
SEED_PROVENANCE = "Project-maintained explicit taxonomy in src/extraction/taxonomy.py"


def seed_taxonomy(session):
    """Idempotent upsert of canonical skills, aliases, categories, and curated parents."""
    aliases_by_name: dict[str, set[str]] = {}
    for alias, canonical in _ALIASES.items():
        aliases_by_name.setdefault(canonical, set()).add(alias)
    names = sorted(aliases_by_name)
    if not names:
        return

    rows = [
        {
            "canonical_name": name,
            "aliases": sorted(aliases_by_name[name]),
            "category": CATEGORIES.get(name, "technology"),
        }
        for name in names
    ]
    session.execute(
        insert(Skill).values(rows).on_conflict_do_nothing(index_elements=[Skill.canonical_name])
    )
    existing = session.scalars(
        select(Skill).where(Skill.canonical_name.in_(names)).order_by(Skill.id).with_for_update()
    ).all()
    by_name = {skill.canonical_name: skill for skill in existing}

    # Preserve independently curated non-default category and parent values.
    for name, skill in by_name.items():
        merged_aliases = sorted(set(skill.aliases or []) | aliases_by_name[name])
        if skill.aliases != merged_aliases:
            skill.aliases = merged_aliases
        target_category = CATEGORIES.get(name, "technology")
        if (
            skill.category is None
            or skill.category == "technology"
            or (
                skill.category == "professional license"
                and target_category == "professional_license"
            )
        ):
            skill.category = target_category
    session.flush()

    for name, parent_name in PARENTS.items():
        skill = by_name.get(name)
        parent = by_name.get(parent_name)
        if skill is not None and parent is not None and skill.parent_skill_id is None:
            skill.parent_skill_id = parent.id
    session.flush()


def persist_requirements(session, job, evidence, text):
    """Replace one current extraction generation atomically with claim completion."""
    seed_taxonomy(session)
    session.execute(delete(JobRequirement).where(JobRequirement.job_id == job.id))
    session.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    skills = {s.canonical_name: s.id for s in session.scalars(select(Skill))}
    selected = annotate_spans(text, evidence)
    associated = set()
    seen = set()
    for item in selected:
        value = text[item["start"] : item["end"]]
        name = item.get("canonical_skill")
        scoring_name = item.get("matched_skill")
        concept = name or value.casefold().strip()
        strength = item["requirement_class"]
        # JobSkill associations support scores only. Approximate matches retain
        # provenance in extraction evidence and never gain a canonical requirement
        # FK or modify aliases. There is no candidate data in these job records.
        if scoring_name and strength is not None and skills[scoring_name] not in associated:
            session.add(JobSkill(job_id=job.id, skill_id=skills[scoring_name]))
            associated.add(skills[scoring_name])
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
