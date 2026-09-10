"""add memory FTS5 index

Revision ID: 7b4e912ad1f0
Revises: bbde382265cb
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "7b4e912ad1f0"
down_revision: Union[str, None] = "bbde382265cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE memory_fts USING fts5(
            memory_id UNINDEXED,
            project_id UNINDEXED,
            subject,
            predicate,
            object_value,
            tokenize='unicode61'
        )
        """
    )
    op.execute(
        """
        INSERT INTO memory_fts(memory_id, project_id, subject, predicate, object_value)
        SELECT id, project_id, subject, predicate, object_value FROM memories
        """
    )
    op.execute(
        """
        CREATE TRIGGER memories_fts_insert AFTER INSERT ON memories BEGIN
            INSERT INTO memory_fts(memory_id, project_id, subject, predicate, object_value)
            VALUES (new.id, new.project_id, new.subject, new.predicate, new.object_value);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER memories_fts_update AFTER UPDATE ON memories BEGIN
            DELETE FROM memory_fts WHERE memory_id = old.id;
            INSERT INTO memory_fts(memory_id, project_id, subject, predicate, object_value)
            VALUES (new.id, new.project_id, new.subject, new.predicate, new.object_value);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER memories_fts_delete AFTER DELETE ON memories BEGIN
            DELETE FROM memory_fts WHERE memory_id = old.id;
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS memories_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS memories_fts_update")
    op.execute("DROP TRIGGER IF EXISTS memories_fts_insert")
    op.execute("DROP TABLE IF EXISTS memory_fts")

