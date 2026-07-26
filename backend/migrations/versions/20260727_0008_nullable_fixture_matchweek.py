"""allow Fixtures awaiting an official Matchweek

Revision ID: 20260727_0008
Revises: 20260727_0007
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fixtures") as batch_op:
        batch_op.alter_column("matchweek", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("fixtures") as batch_op:
        batch_op.alter_column("matchweek", existing_type=sa.Integer(), nullable=False)
