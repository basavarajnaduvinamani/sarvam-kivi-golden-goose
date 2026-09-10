from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def rebuild_memory_fts(session: Session) -> int:
    """Rebuild FTS only from active memories whose required evidence is still valid."""
    session.execute(text("DELETE FROM memory_fts"))
    session.execute(
        text(
            """
            INSERT INTO memory_fts(memory_id, project_id, subject, predicate, object_value)
            SELECT m.id, m.project_id, m.subject, m.predicate, m.object_value
            FROM memories AS m
            WHERE m.lifecycle_status = 'ACTIVE'
              AND EXISTS (
                  SELECT 1 FROM memory_evidence AS e JOIN takes AS t ON t.id = e.take_id
                  WHERE e.memory_id = m.id AND e.is_required = 1 AND t.is_deleted = 0
              )
              AND NOT EXISTS (
                  SELECT 1 FROM memory_evidence AS e JOIN takes AS t ON t.id = e.take_id
                  WHERE e.memory_id = m.id AND e.is_required = 1 AND t.is_deleted = 1
              )
            """
        )
    )
    return int(session.scalar(text("SELECT count(*) FROM memory_fts")) or 0)
