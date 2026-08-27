"""Add per-user learning progress.

Revision ID: 20260821_03
Revises: 20260821_02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_03"
down_revision = "20260821_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="started"),
        sa.Column("best_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["learning_lessons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_learning_progress_user_lesson"),
    )
    op.create_index("ix_learning_progress_user_id", "learning_progress", ["user_id"])
    op.create_index("ix_learning_progress_lesson_id", "learning_progress", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_progress_lesson_id", table_name="learning_progress")
    op.drop_index("ix_learning_progress_user_id", table_name="learning_progress")
    op.drop_table("learning_progress")
