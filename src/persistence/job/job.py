from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class JobStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


ALLOWED_STATUS_TRANSITIONS = {
    JobStatus.DISCOVERED: {JobStatus.ACTIVE, JobStatus.EXPIRED},
    JobStatus.ACTIVE: {JobStatus.STALE, JobStatus.EXPIRED},
    JobStatus.STALE: {JobStatus.ACTIVE, JobStatus.EXPIRED},
    JobStatus.EXPIRED: set(),
}


def can_transition_to(current_status: JobStatus, new_status: JobStatus) -> bool:
    return new_status in ALLOWED_STATUS_TRANSITIONS[current_status]


class Job(Base):
    __tablename__ = "jobs"


    __table_args__ = (
    UniqueConstraint("source", "source_job_id"),
    Index("ix_jobs_status", "status"),
    Index("ix_jobs_published_at", "published_at"),)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)

    company: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    mode: Mapped[str | None] = mapped_column(String(50))

    salary: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(10))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    requirements: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[JobStatus] = mapped_column(
        SQLAlchemyEnum(JobStatus),
        nullable=False,
        default=JobStatus.DISCOVERED,
    )

    canonical_url: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
    content_hash: Mapped[str | None] = mapped_column(String(64))
