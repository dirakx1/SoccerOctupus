"""add league standings persistence

Revision ID: 20260727_0006
Revises: 20260624_0005
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0006"
down_revision = "20260624_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("teams", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slug", sa.String(128), nullable=False, unique=True), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("abbreviation", sa.String(16)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_teams_slug", "teams", ["slug"])
    op.create_table("competition_editions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("competition_slug", sa.String(128), nullable=False), sa.Column("edition_slug", sa.String(64), nullable=False), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("configuration_revision", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("competition_slug", "edition_slug", name="uq_competition_edition"))
    op.create_index("ix_competition_editions_competition_slug", "competition_editions", ["competition_slug"])
    op.create_table("competition_edition_teams", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("competition_edition_id", sa.Integer(), sa.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False), sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("competition_edition_id", "team_id", name="uq_edition_team"))
    op.create_table("team_provider_mappings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_team_id", sa.String(128), nullable=False), sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("provider", "provider_team_id", name="uq_provider_team_id"), sa.UniqueConstraint("provider", "team_id", name="uq_provider_team"))
    op.create_table("standings_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("competition_edition_id", sa.Integer(), sa.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False), sa.Column("source", sa.String(32), nullable=False), sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("competition_edition_id", "content_hash", name="uq_edition_standings_hash"))
    op.create_index("ix_standings_snapshots_competition_edition_id", "standings_snapshots", ["competition_edition_id"])
    op.create_table("standings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("standings_snapshots.id", ondelete="CASCADE"), nullable=False), sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("played", sa.Integer(), nullable=False), sa.Column("won", sa.Integer(), nullable=False), sa.Column("drawn", sa.Integer(), nullable=False), sa.Column("lost", sa.Integer(), nullable=False), sa.Column("goals_for", sa.Integer(), nullable=False), sa.Column("goals_against", sa.Integer(), nullable=False), sa.Column("goal_difference", sa.Integer(), nullable=False), sa.Column("points", sa.Integer(), nullable=False), sa.UniqueConstraint("snapshot_id", "position", name="uq_snapshot_position"), sa.UniqueConstraint("snapshot_id", "team_id", name="uq_snapshot_team"))
    op.create_index("ix_standings_snapshot_id", "standings", ["snapshot_id"])


def downgrade() -> None:
    op.drop_table("standings")
    op.drop_table("standings_snapshots")
    op.drop_table("team_provider_mappings")
    op.drop_table("competition_edition_teams")
    op.drop_table("competition_editions")
    op.drop_table("teams")
