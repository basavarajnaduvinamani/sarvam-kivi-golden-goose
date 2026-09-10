from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Memory, MemoryEvidence, Project
from ..schemas import ProjectRead, ProjectTimelineResponse, TimelineEntryRead, TimelineEvidenceRead


class TimelineError(ValueError):
    pass


def get_project_timeline(session: Session, project_id: str) -> ProjectTimelineResponse:
    project = session.get(Project, project_id)
    if project is None:
        raise TimelineError(f"unknown project_id: {project_id}")
    memories = list(
        session.scalars(
            select(Memory)
            .where(Memory.project_id == project_id)
            .options(selectinload(Memory.evidence_links).selectinload(MemoryEvidence.take))
            .order_by(Memory.created_at, Memory.id)
        )
    )
    superseded_by: dict[str, list[str]] = defaultdict(list)
    for memory in memories:
        if memory.supersedes_memory_id:
            superseded_by[memory.supersedes_memory_id].append(memory.id)
    entries = [
        TimelineEntryRead(
            memory_id=memory.id,
            memory_type=memory.memory_type,
            subject=memory.subject,
            predicate=memory.predicate,
            object_value=memory.object_value,
            epistemic_status=memory.epistemic_status,
            lifecycle_status=memory.lifecycle_status,
            valid_from=memory.valid_from,
            valid_to=memory.valid_to,
            created_at=memory.created_at,
            supersedes_memory_id=memory.supersedes_memory_id,
            superseded_by_memory_ids=sorted(superseded_by[memory.id]),
            evidence=[
                TimelineEvidenceRead(
                    take_id=link.take_id,
                    source_application=link.take.source_application,
                    event_ts=link.take.event_ts,
                    span_start=link.span_start,
                    span_end=link.span_end,
                    evidence_role=link.evidence_role,
                    is_required=link.is_required,
                    is_deleted=link.take.is_deleted,
                )
                for link in sorted(memory.evidence_links, key=lambda item: (item.take.event_ts, item.take_id))
            ],
        )
        for memory in memories
    ]
    entries.sort(key=lambda entry: (min((item.event_ts for item in entry.evidence), default=entry.created_at), entry.memory_id))
    return ProjectTimelineResponse(project=ProjectRead.model_validate(project), entries=entries)
