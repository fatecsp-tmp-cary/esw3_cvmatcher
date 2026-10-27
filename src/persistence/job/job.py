from datetime import UTC, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class WorkArrangement(StrEnum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"


class SeniorityLevel(StrEnum):
    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    SPECIALIST = "SPECIALIST"
    COORDINATOR = "COORDINATOR"


class JobStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        UniqueConstraint(
            "platform",
            "source_job_id",
            name="uq_jobs_platform_source_job_id",
        ),
        Index("ix_jobs_publication_date", "publication_date"),
        Index("ix_jobs_source_id", "source_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("job_sources.id"),
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[dict[str, str | None] | None] = mapped_column(JSON)
    work_arrangement: Mapped[WorkArrangement | None] = mapped_column(
        SQLAlchemyEnum(WorkArrangement, name="workarrangement")
    )
    seniority_level: Mapped[SeniorityLevel | None] = mapped_column(
        SQLAlchemyEnum(SeniorityLevel, name="senioritylevel")
    )
    skills: Mapped[list[str] | None] = mapped_column(JSON)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    salary: Mapped[dict[str, int | float | str | None] | None] = mapped_column(JSON)
    currency: Mapped[str | None] = mapped_column(String(10))
    job_url: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[JobStatus] = mapped_column(
        SQLAlchemyEnum(JobStatus, name="jobstatus"),
        nullable=False,
        default=JobStatus.DISCOVERED,
        server_default=JobStatus.DISCOVERED.value,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict[str, object] | None] = mapped_column(JSON)
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
    content_hash: Mapped[str | None] = mapped_column(String(255))
