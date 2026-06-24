"""add stripe subscriptions

Revision ID: 20260619_0004
Revises: 20260615_0003
Create Date: 2026-06-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0004"
down_revision = "20260615_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("stripe_price_id", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("subscription_tier", sa.String(length=32), nullable=False, server_default="free"),
    )
    op.add_column("users", sa.Column("subscription_status", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("subscription_cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("subscription_synced_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_users_stripe_customer_id"), "users", ["stripe_customer_id"], unique=True)
    op.create_index(op.f("ix_users_stripe_subscription_id"), "users", ["stripe_subscription_id"], unique=True)
    op.create_index(op.f("ix_users_stripe_price_id"), "users", ["stripe_price_id"], unique=False)
    op.create_index(op.f("ix_users_subscription_tier"), "users", ["subscription_tier"], unique=False)
    op.create_index(op.f("ix_users_subscription_status"), "users", ["subscription_status"], unique=False)

    op.create_table(
        "stripe_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stripe_events_stripe_event_id"), "stripe_events", ["stripe_event_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_stripe_events_stripe_event_id"), table_name="stripe_events")
    op.drop_table("stripe_events")
    op.drop_index(op.f("ix_users_subscription_status"), table_name="users")
    op.drop_index(op.f("ix_users_subscription_tier"), table_name="users")
    op.drop_index(op.f("ix_users_stripe_price_id"), table_name="users")
    op.drop_index(op.f("ix_users_stripe_subscription_id"), table_name="users")
    op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
    op.drop_column("users", "subscription_synced_at")
    op.drop_column("users", "subscription_cancel_at_period_end")
    op.drop_column("users", "subscription_current_period_end")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_tier")
    op.drop_column("users", "stripe_price_id")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
