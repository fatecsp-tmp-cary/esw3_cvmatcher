from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    polling_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    polling_interval: Mapped[int | None] = mapped_column(Integer)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_error: Mapped[str | None] = mapped_column(Text)
