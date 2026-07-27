"""add historical club matches and prediction grants

Revision ID: 20260727_0010
Revises: 20260727_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_competition", sa.String(64), nullable=False),
        sa.Column("source_edition", sa.String(32), nullable=False),
        sa.Column("provider_match_id", sa.String(128), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "provider_match_id", name="uq_club_match_source_provider"),
    )
    op.create_index("ix_club_matches_source_competition", "club_matches", ["source_competition"])
    op.create_index("ix_club_matches_source_edition", "club_matches", ["source_edition"])
    op.create_index("ix_club_matches_played_at", "club_matches", ["played_at"])
    op.create_table(
        "match_prediction_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fixture_id", "fingerprint", name="uq_match_prediction_fixture_fingerprint"),
    )
    op.create_index("ix_match_prediction_versions_fixture_id", "match_prediction_versions", ["fixture_id"])
    op.create_table(
        "user_match_prediction_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prediction_version_id", sa.Integer(), sa.ForeignKey("match_prediction_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cycle_limit_id", sa.Integer(), sa.ForeignKey("user_feature_cycle_limits.id", ondelete="SET NULL")),
        sa.Column("charged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "prediction_version_id", name="uq_user_match_prediction_grant"),
    )
    op.create_index("ix_user_match_prediction_grants_user_id", "user_match_prediction_grants", ["user_id"])
    op.create_index("ix_user_match_prediction_grants_prediction_version_id", "user_match_prediction_grants", ["prediction_version_id"])


def downgrade() -> None:
    op.drop_table("user_match_prediction_grants")
    op.drop_table("match_prediction_versions")
    op.drop_table("club_matches")
