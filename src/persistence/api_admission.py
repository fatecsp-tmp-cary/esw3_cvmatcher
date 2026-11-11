"""Anonymous admission timestamps, included in Alembic metadata.

Rows intentionally have no client identity or payload and need no ORM identity.
"""

from sqlalchemy import Column, DateTime, Table

from src.persistence.base import Base

api_admissions = Table(
    "api_admissions", Base.metadata, Column("admitted_at", DateTime(timezone=True), nullable=False)
)
