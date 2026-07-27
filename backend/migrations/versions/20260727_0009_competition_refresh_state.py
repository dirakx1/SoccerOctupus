"""add competition edition refresh state

Revision ID: 20260727_0009
Revises: 20260727_0008
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "competition_edition_refreshes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition_edition_id", sa.Integer(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("refresh_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["competition_edition_id"], ["competition_editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition_edition_id"),
    )
    op.create_index(
        op.f("ix_competition_edition_refreshes_competition_edition_id"),
        "competition_edition_refreshes",
        ["competition_edition_id"],
        unique=True,
    )
    op.execute(sa.text("""
        INSERT INTO competition_edition_refreshes
            (competition_edition_id, source_updated_at, last_attempt_at, created_at, updated_at)
        SELECT ce.id, MAX(ss.source_updated_at), MAX(ss.source_updated_at), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM competition_editions ce
        JOIN standings_snapshots ss ON ss.competition_edition_id = ce.id
        GROUP BY ce.id
    """))


def downgrade():
    op.drop_index(
        op.f("ix_competition_edition_refreshes_competition_edition_id"),
        table_name="competition_edition_refreshes",
    )
    op.drop_table("competition_edition_refreshes")
