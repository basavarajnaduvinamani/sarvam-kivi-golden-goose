"""add evidence sufficiency and internal query errors

Revision ID: d164b8a1c321
Revises: 7b4e912ad1f0
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d164b8a1c321"
down_revision: Union[str, None] = "7b4e912ad1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("memory_evidence") as batch_op:
        batch_op.add_column(sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("query_runs") as batch_op:
        batch_op.add_column(sa.Column("error_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("query_runs") as batch_op:
        batch_op.drop_column("error_detail")
    with op.batch_alter_table("memory_evidence") as batch_op:
        batch_op.drop_column("is_required")
