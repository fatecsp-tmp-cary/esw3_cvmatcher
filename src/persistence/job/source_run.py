from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class SourceRun(Base):
    __tablename__ = "source_runs"

    __table_args__ = (Index("ix_source_runs_source_id", "source_id"),)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("job_sources.id"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    snapshot_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    polling_mode: Mapped[str] = mapped_column(String(50), nullable=False)

    duration_ms: Mapped[int | None] = mapped_column(Integer)

    jobs_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_created: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_unchanged: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_absent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_marked_stale: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_expired: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    jobs_reactivated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    errors: Mapped[str | None] = mapped_column(Text)
