"""add league fixture persistence

Revision ID: 20260727_0007
Revises: 20260727_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_edition_id", sa.Integer(), sa.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("matchweek", sa.Integer(), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider_status", sa.String(128), nullable=False),
        sa.Column("home_score", sa.Integer()),
        sa.Column("away_score", sa.Integer()),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fixtures_competition_edition_id", "fixtures", ["competition_edition_id"])
    op.create_index("ix_fixtures_matchweek", "fixtures", ["matchweek"])
    op.create_index("ix_fixtures_kickoff_at", "fixtures", ["kickoff_at"])
    op.create_index("ix_fixtures_status", "fixtures", ["status"])
    op.create_table(
        "fixture_provider_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_fixture_id", sa.String(128), nullable=False),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_fixture_id", name="uq_provider_fixture_id"),
        sa.UniqueConstraint("provider", "fixture_id", name="uq_provider_fixture"),
    )


def downgrade() -> None:
    op.drop_table("fixture_provider_mappings")
    op.drop_table("fixtures")
