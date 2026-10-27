"""Shared skill taxonomy and normalized job skill associations."""

from enum import StrEnum

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class RequirementClass(StrEnum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    NICE_TO_HAVE = "NICE_TO_HAVE"


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(100))
    parent_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL")
    )
    aliases: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    __table_args__ = (Index("ix_job_skills_skill_id", "skill_id"),)

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    __table_args__ = (Index("ix_job_requirements_job_id", "job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_class: Mapped[RequirementClass] = mapped_column(
        SQLAlchemyEnum(RequirementClass, name="requirementclass"), nullable=False
    )
    skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL")
    )
