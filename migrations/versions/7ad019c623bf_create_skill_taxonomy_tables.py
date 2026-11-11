"""Create shared skills and normalized job requirement tables.

Revision ID: 7ad019c623bf
Revises: 6f4ad83a91c0
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ad019c623bf"
down_revision: str | Sequence[str] | None = "6f4ad83a91c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the shared taxonomy and per-job skill/requirement links."""
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("parent_skill_id", sa.Integer(), nullable=True),
        sa.Column("aliases", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_skill_id"],
            ["skills.id"],
            name=op.f("fk_skills_parent_skill_id_skills"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("canonical_name", name="uq_skills_canonical_name"),
    )
    op.create_table(
        "job_skills",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_skills_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_job_skills_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", "skill_id", name=op.f("pk_job_skills")),
    )
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "requirement_class",
            sa.Enum(
                "REQUIRED",
                "PREFERRED",
                "NICE_TO_HAVE",
                name="requirementclass",
            ),
            nullable=False,
        ),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_requirements_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_job_requirements_skill_id_skills"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_requirements")),
    )
    op.create_index("ix_job_requirements_job_id", "job_requirements", ["job_id"])


def downgrade() -> None:
    """Drop job requirement links and the shared taxonomy."""
    op.drop_index("ix_job_requirements_job_id", table_name="job_requirements")
    op.drop_table("job_requirements")
    op.drop_index("ix_job_skills_skill_id", table_name="job_skills")
    op.drop_table("job_skills")
    op.drop_table("skills")
    sa.Enum(name="requirementclass").drop(op.get_bind(), checkfirst=True)
