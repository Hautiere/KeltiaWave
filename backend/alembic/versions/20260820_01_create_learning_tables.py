"""Create KeltiaWave Learn tables.

Revision ID: 20260820_01
Revises:
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("draft", "published", "archived", name="learninglessonstatus", native_enum=False), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_lessons_created_by_id", "learning_lessons", ["created_by_id"])
    op.create_index("ix_learning_lessons_status", "learning_lessons", ["status"])

    op.create_table(
        "learning_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["learning_lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_learning_videos_lesson_id", "learning_videos", ["lesson_id"])

    op.create_table(
        "learning_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("translation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["learning_lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_segments_lesson_id", "learning_segments", ["lesson_id"])

    op.create_table(
        "learning_blanks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("answer", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["learning_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_blanks_segment_id", "learning_blanks", ["segment_id"])

    op.create_table(
        "learning_vocabulary_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("translation", sa.String(length=500), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["learning_lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_vocabulary_items_lesson_id", "learning_vocabulary_items", ["lesson_id"])

    op.create_table(
        "learning_grammar_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("translation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["learning_lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_grammar_items_lesson_id", "learning_grammar_items", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_grammar_items_lesson_id", table_name="learning_grammar_items")
    op.drop_table("learning_grammar_items")
    op.drop_index("ix_learning_vocabulary_items_lesson_id", table_name="learning_vocabulary_items")
    op.drop_table("learning_vocabulary_items")
    op.drop_index("ix_learning_blanks_segment_id", table_name="learning_blanks")
    op.drop_table("learning_blanks")
    op.drop_index("ix_learning_segments_lesson_id", table_name="learning_segments")
    op.drop_table("learning_segments")
    op.drop_index("ix_learning_videos_lesson_id", table_name="learning_videos")
    op.drop_table("learning_videos")
    op.drop_index("ix_learning_lessons_status", table_name="learning_lessons")
    op.drop_index("ix_learning_lessons_created_by_id", table_name="learning_lessons")
    op.drop_table("learning_lessons")
