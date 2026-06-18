"""add encrypted app settings secrets

Revision ID: 20260615_0002
Revises: 20260611_0001
Create Date: 2026-06-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260615_0002"
down_revision = "20260611_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("app_settings", sa.Column("zep_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("app_settings", sa.Column("youtube_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("app_settings", sa.Column("opta_api_key_encrypted", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE app_settings
            SET swarm_parallel_agents = 7
            WHERE scope = 'global' AND swarm_parallel_agents = 5
            """
        )
    )


def downgrade() -> None:
    op.drop_column("app_settings", "opta_api_key_encrypted")
    op.drop_column("app_settings", "youtube_api_key_encrypted")
    op.drop_column("app_settings", "zep_api_key_encrypted")
    op.drop_column("app_settings", "llm_api_key_encrypted")
