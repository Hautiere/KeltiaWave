"""Add accepted variants and mutation tolerance to learning blanks.

Revision ID: 20260822_06
Revises: 20260821_05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260822_06"
down_revision = "20260821_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_blanks",
        sa.Column("accepted_variants", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "learning_blanks",
        sa.Column("accept_mutations", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("learning_blanks", "accept_mutations")
    op.drop_column("learning_blanks", "accepted_variants")
