"""Persistence models."""

from __future__ import annotations

from datetime import datetime, timezone

from .base import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    clerk_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_sign_in_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    stripe_price_id = db.Column(db.String(255), nullable=True, index=True)
    subscription_tier = db.Column(db.String(32), nullable=False, default="free", index=True)
    subscription_status = db.Column(db.String(64), nullable=True, index=True)
    subscription_current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
    subscription_cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    subscription_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)


class StripeEvent(db.Model, TimestampMixin):
    __tablename__ = "stripe_events"

    id = db.Column(db.Integer, primary_key=True)
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(255), nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)


class AppSettings(db.Model, TimestampMixin):
    __tablename__ = "app_settings"

    scope = db.Column(db.String(64), primary_key=True, default="global")
    llm_base_url = db.Column(db.String(255), nullable=False)
    llm_model_name = db.Column(db.String(255), nullable=False)
    zep_graph_id = db.Column(db.String(255), nullable=True)
    opta_base_url = db.Column(db.String(255), nullable=False)
    llm_api_key_encrypted = db.Column(db.Text, nullable=True)
    zep_api_key_encrypted = db.Column(db.Text, nullable=True)
    youtube_api_key_encrypted = db.Column(db.Text, nullable=True)
    opta_api_key_encrypted = db.Column(db.Text, nullable=True)
    swarm_parallel_agents = db.Column(db.Integer, nullable=False)
    swarm_timeout_seconds = db.Column(db.Integer, nullable=False)
    mc_simulations = db.Column(db.Integer, nullable=False)
    updated_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id], lazy="joined")
