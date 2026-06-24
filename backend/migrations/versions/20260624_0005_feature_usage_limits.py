"""add feature usage limits

Revision ID: 20260624_0005
Revises: 20260619_0004
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_0005"
down_revision = "20260619_0004"
branch_labels = None
depends_on = None


FEATURE_LIMIT_POLICIES = [
    ("free", "match_prediction", 1),
    ("free", "tournament_simulation", 1),
    ("free", "match_market", 3),
    ("free", "tournament_market", 3),
    ("basic", "match_prediction", None),
    ("basic", "tournament_simulation", None),
    ("basic", "match_market", None),
    ("basic", "tournament_market", None),
    ("pro", "match_prediction", None),
    ("pro", "tournament_simulation", None),
    ("pro", "match_market", None),
    ("pro", "tournament_market", None),
]


def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_current_period_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("usage_cycle_anchor_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET usage_cycle_anchor_at = created_at WHERE usage_cycle_anchor_at IS NULL")

    op.create_table(
        "feature_limit_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("limit_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tier", "feature_key", name="uq_feature_limit_policy_tier_feature"),
    )
    op.create_index(op.f("ix_feature_limit_policies_tier"), "feature_limit_policies", ["tier"], unique=False)
    op.create_index(op.f("ix_feature_limit_policies_feature_key"), "feature_limit_policies", ["feature_key"], unique=False)

    op.create_table(
        "user_feature_limit_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("limit_count", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_feature_limit_overrides_user_id"), "user_feature_limit_overrides", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_feature_limit_overrides_feature_key"), "user_feature_limit_overrides", ["feature_key"], unique=False)
    op.create_index(op.f("ix_user_feature_limit_overrides_is_active"), "user_feature_limit_overrides", ["is_active"], unique=False)

    op.create_table(
        "user_feature_cycle_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("cycle_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cycle_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("limit_count", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_source", sa.String(length=32), nullable=False, server_default="policy"),
        sa.Column("override_note", sa.Text(), nullable=True),
        sa.Column("overridden_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["overridden_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "feature_key", "cycle_start", "cycle_end", name="uq_user_feature_cycle_limit"),
    )
    op.create_index(op.f("ix_user_feature_cycle_limits_user_id"), "user_feature_cycle_limits", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_feature_cycle_limits_tier"), "user_feature_cycle_limits", ["tier"], unique=False)
    op.create_index(op.f("ix_user_feature_cycle_limits_feature_key"), "user_feature_cycle_limits", ["feature_key"], unique=False)
    op.create_index(op.f("ix_user_feature_cycle_limits_cycle_start"), "user_feature_cycle_limits", ["cycle_start"], unique=False)
    op.create_index(op.f("ix_user_feature_cycle_limits_cycle_end"), "user_feature_cycle_limits", ["cycle_end"], unique=False)

    policies = sa.table(
        "feature_limit_policies",
        sa.column("tier", sa.String),
        sa.column("feature_key", sa.String),
        sa.column("limit_count", sa.Integer),
    )
    op.bulk_insert(
        policies,
        [{"tier": tier, "feature_key": feature_key, "limit_count": limit_count} for tier, feature_key, limit_count in FEATURE_LIMIT_POLICIES],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_feature_cycle_limits_cycle_end"), table_name="user_feature_cycle_limits")
    op.drop_index(op.f("ix_user_feature_cycle_limits_cycle_start"), table_name="user_feature_cycle_limits")
    op.drop_index(op.f("ix_user_feature_cycle_limits_feature_key"), table_name="user_feature_cycle_limits")
    op.drop_index(op.f("ix_user_feature_cycle_limits_tier"), table_name="user_feature_cycle_limits")
    op.drop_index(op.f("ix_user_feature_cycle_limits_user_id"), table_name="user_feature_cycle_limits")
    op.drop_table("user_feature_cycle_limits")
    op.drop_index(op.f("ix_user_feature_limit_overrides_is_active"), table_name="user_feature_limit_overrides")
    op.drop_index(op.f("ix_user_feature_limit_overrides_feature_key"), table_name="user_feature_limit_overrides")
    op.drop_index(op.f("ix_user_feature_limit_overrides_user_id"), table_name="user_feature_limit_overrides")
    op.drop_table("user_feature_limit_overrides")
    op.drop_index(op.f("ix_feature_limit_policies_feature_key"), table_name="feature_limit_policies")
    op.drop_index(op.f("ix_feature_limit_policies_tier"), table_name="feature_limit_policies")
    op.drop_table("feature_limit_policies")
    op.drop_column("users", "usage_cycle_anchor_at")
    op.drop_column("users", "subscription_current_period_start")
