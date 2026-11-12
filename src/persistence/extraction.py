"""Job-only extraction readiness; deliberately separate from canonical Job."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class JobExtraction(Base):
    __tablename__ = "job_extractions"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')", name="status"),
        CheckConstraint("attempts >= 0 AND attempts <= 3", name="attempts"),
        CheckConstraint("(status = 'RUNNING') = (claim_token IS NOT NULL)", name="claim"),
        CheckConstraint("(status = 'RUNNING') = (lease_expires_at IS NOT NULL)", name="lease"),
        Index("ix_job_extractions_pending", "status", "next_attempt_at", "job_id"),
    )

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    config_version: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claim_token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(32))
    evidence: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB)
