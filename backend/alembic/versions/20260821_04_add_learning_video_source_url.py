"""Add the original source URL to learning media.

Revision ID: 20260821_04
Revises: 20260821_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_04"
down_revision = "20260821_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_videos", sa.Column("source_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_videos", "source_url")
