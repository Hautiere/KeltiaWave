"""Add a customizable source link label to learning media.

Revision ID: 20260821_05
Revises: 20260821_04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_05"
down_revision = "20260821_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_videos", sa.Column("source_link_label", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_videos", "source_link_label")
