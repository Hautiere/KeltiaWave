"""Add lesson thumbnail metadata.

Revision ID: 20260821_02
Revises: 20260820_01
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_02"
down_revision = "20260820_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("learning_lessons") as batch_op:
        batch_op.add_column(sa.Column("thumbnail_original_filename", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_storage_key", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_content_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_size_bytes", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_learning_lessons_thumbnail_storage_key", ["thumbnail_storage_key"])


def downgrade() -> None:
    with op.batch_alter_table("learning_lessons") as batch_op:
        batch_op.drop_constraint("uq_learning_lessons_thumbnail_storage_key", type_="unique")
        batch_op.drop_column("thumbnail_size_bytes")
        batch_op.drop_column("thumbnail_content_type")
        batch_op.drop_column("thumbnail_storage_key")
        batch_op.drop_column("thumbnail_original_filename")
