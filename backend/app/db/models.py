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
    subscription_current_period_start = db.Column(db.DateTime(timezone=True), nullable=True)
    subscription_current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
    subscription_cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    subscription_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    usage_cycle_anchor_at = db.Column(db.DateTime(timezone=True), nullable=True)


class StripeEvent(db.Model, TimestampMixin):
    __tablename__ = "stripe_events"

    id = db.Column(db.Integer, primary_key=True)
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(255), nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)


class FeatureLimitPolicy(db.Model, TimestampMixin):
    __tablename__ = "feature_limit_policies"
    __table_args__ = (db.UniqueConstraint("tier", "feature_key", name="uq_feature_limit_policy_tier_feature"),)

    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.String(32), nullable=False, index=True)
    feature_key = db.Column(db.String(64), nullable=False, index=True)
    limit_count = db.Column(db.Integer, nullable=True)


class UserFeatureLimitOverride(db.Model, TimestampMixin):
    __tablename__ = "user_feature_limit_overrides"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key = db.Column(db.String(64), nullable=False, index=True)
    limit_count = db.Column(db.Integer, nullable=True)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note = db.Column(db.Text, nullable=True)


class UserFeatureCycleLimit(db.Model, TimestampMixin):
    __tablename__ = "user_feature_cycle_limits"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "feature_key",
            "cycle_start",
            "cycle_end",
            name="uq_user_feature_cycle_limit",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tier = db.Column(db.String(32), nullable=False, index=True)
    feature_key = db.Column(db.String(64), nullable=False, index=True)
    cycle_start = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    cycle_end = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    limit_count = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    limit_source = db.Column(db.String(32), nullable=False, default="policy")
    override_note = db.Column(db.Text, nullable=True)
    overridden_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


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


class Team(db.Model, TimestampMixin):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    abbreviation = db.Column(db.String(16), nullable=True)


class CompetitionEdition(db.Model, TimestampMixin):
    __tablename__ = "competition_editions"
    __table_args__ = (
        db.UniqueConstraint("competition_slug", "edition_slug", name="uq_competition_edition"),
    )

    id = db.Column(db.Integer, primary_key=True)
    competition_slug = db.Column(db.String(128), nullable=False, index=True)
    edition_slug = db.Column(db.String(64), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    configuration_revision = db.Column(db.String(64), nullable=False)


class CompetitionEditionRefresh(db.Model, TimestampMixin):
    __tablename__ = "competition_edition_refreshes"

    id = db.Column(db.Integer, primary_key=True)
    competition_edition_id = db.Column(
        db.Integer,
        db.ForeignKey("competition_editions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_attempt_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_error = db.Column(db.Text, nullable=True)
    refresh_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    refresh_lease_until = db.Column(db.DateTime(timezone=True), nullable=True)


class CompetitionEditionTeam(db.Model, TimestampMixin):
    __tablename__ = "competition_edition_teams"
    __table_args__ = (
        db.UniqueConstraint("competition_edition_id", "team_id", name="uq_edition_team"),
    )

    id = db.Column(db.Integer, primary_key=True)
    competition_edition_id = db.Column(
        db.Integer, db.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False
    )
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team = db.relationship("Team", lazy="joined")


class TeamProviderMapping(db.Model, TimestampMixin):
    __tablename__ = "team_provider_mappings"
    __table_args__ = (
        db.UniqueConstraint("provider", "provider_team_id", name="uq_provider_team_id"),
        db.UniqueConstraint("provider", "team_id", name="uq_provider_team"),
    )

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(32), nullable=False)
    provider_team_id = db.Column(db.String(128), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team = db.relationship("Team", lazy="joined")


class Fixture(db.Model, TimestampMixin):
    __tablename__ = "fixtures"

    id = db.Column(db.Integer, primary_key=True)
    competition_edition_id = db.Column(
        db.Integer, db.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    matchweek = db.Column(db.Integer, nullable=True, index=True)
    kickoff_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    venue = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    provider_status = db.Column(db.String(128), nullable=False)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    home_team = db.relationship("Team", foreign_keys=[home_team_id], lazy="joined")
    away_team = db.relationship("Team", foreign_keys=[away_team_id], lazy="joined")


class FixtureProviderMapping(db.Model, TimestampMixin):
    __tablename__ = "fixture_provider_mappings"
    __table_args__ = (
        db.UniqueConstraint("provider", "provider_fixture_id", name="uq_provider_fixture_id"),
        db.UniqueConstraint("provider", "fixture_id", name="uq_provider_fixture"),
    )

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(32), nullable=False)
    provider_fixture_id = db.Column(db.String(128), nullable=False)
    fixture_id = db.Column(db.Integer, db.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False)
    fixture = db.relationship("Fixture", lazy="joined")


class ClubMatch(db.Model, TimestampMixin):
    __tablename__ = "club_matches"
    __table_args__ = (
        db.UniqueConstraint("source", "provider_match_id", name="uq_club_match_source_provider"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(32), nullable=False)
    source_competition = db.Column(db.String(64), nullable=False, index=True)
    source_edition = db.Column(db.String(32), nullable=False, index=True)
    provider_match_id = db.Column(db.String(128), nullable=False)
    played_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    home_score = db.Column(db.Integer, nullable=False)
    away_score = db.Column(db.Integer, nullable=False)
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    home_team = db.relationship("Team", foreign_keys=[home_team_id], lazy="joined")
    away_team = db.relationship("Team", foreign_keys=[away_team_id], lazy="joined")


class MatchPredictionVersion(db.Model):
    __tablename__ = "match_prediction_versions"
    __table_args__ = (
        db.UniqueConstraint("fixture_id", "fingerprint", name="uq_match_prediction_fixture_fingerprint"),
    )

    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey("fixtures.id", ondelete="RESTRICT"), nullable=False, index=True)
    fingerprint = db.Column(db.String(64), nullable=False)
    model_version = db.Column(db.String(64), nullable=False)
    source = db.Column(db.String(64), nullable=False)
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    forecast = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    fixture = db.relationship("Fixture", lazy="joined")


class UserMatchPredictionGrant(db.Model):
    __tablename__ = "user_match_prediction_grants"
    __table_args__ = (
        db.UniqueConstraint("user_id", "prediction_version_id", name="uq_user_match_prediction_grant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_version_id = db.Column(
        db.Integer,
        db.ForeignKey("match_prediction_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cycle_limit_id = db.Column(
        db.Integer,
        db.ForeignKey("user_feature_cycle_limits.id", ondelete="SET NULL"),
        nullable=True,
    )
    charged = db.Column(db.Boolean, nullable=False, default=False)
    revealed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    prediction_version = db.relationship("MatchPredictionVersion", lazy="joined")


class StandingsSnapshot(db.Model, TimestampMixin):
    __tablename__ = "standings_snapshots"
    __table_args__ = (
        db.UniqueConstraint("competition_edition_id", "content_hash", name="uq_edition_standings_hash"),
    )

    id = db.Column(db.Integer, primary_key=True)
    competition_edition_id = db.Column(
        db.Integer, db.ForeignKey("competition_editions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source = db.Column(db.String(32), nullable=False)
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    standings = db.relationship(
        "Standing", back_populates="snapshot", cascade="all, delete-orphan", order_by="Standing.position"
    )


class Standing(db.Model):
    __tablename__ = "standings"
    __table_args__ = (
        db.UniqueConstraint("snapshot_id", "position", name="uq_snapshot_position"),
        db.UniqueConstraint("snapshot_id", "team_id", name="uq_snapshot_team"),
    )

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(
        db.Integer, db.ForeignKey("standings_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    played = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Integer, nullable=False)
    drawn = db.Column(db.Integer, nullable=False)
    lost = db.Column(db.Integer, nullable=False)
    goals_for = db.Column(db.Integer, nullable=False)
    goals_against = db.Column(db.Integer, nullable=False)
    goal_difference = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    snapshot = db.relationship("StandingsSnapshot", back_populates="standings")
    team = db.relationship("Team", lazy="joined")
