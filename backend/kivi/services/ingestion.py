from __future__ import annotations

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..enums import LifecycleStatus
from ..models import Memory, MemoryEvidence, Project, Take
from ..presenters import present_memory
from ..providers import Embedder, MemoryExtractor
from ..schemas import TakeCreate, TakeIngestResult, TakeRead
from ..serialization import vector_to_blob


class IngestionError(ValueError):
    pass


def ingest_take(
    session: Session,
    payload: TakeCreate,
    extractor: MemoryExtractor,
    embedder: Embedder,
) -> TakeIngestResult:
    project = session.get(Project, payload.project_id) if payload.project_id else None
    if payload.project_id is not None and project is None:
        raise IngestionError(f"unknown project_id: {payload.project_id}")
    if session.get(Take, payload.take_id) is not None:
        raise IngestionError(f"duplicate take_id: {payload.take_id}")

    embedding_result = embedder.embed(payload.formatted_text)
    take = Take(
        id=payload.take_id,
        project_id=payload.project_id,
        raw_asr=payload.raw_asr,
        formatted_text=payload.formatted_text,
        source_application=payload.source_application,
        event_ts=payload.event_ts,
        source_metadata=payload.metadata,
        embedding=vector_to_blob(embedding_result.vector),
        embedding_model=embedding_result.usage.model_name,
    )
    session.add(take)

    if project is None:
        session.commit()
        session.refresh(take)
        return TakeIngestResult(
            take=TakeRead.model_validate(take),
            memories=[],
            ignored_reason="Project scope is unresolved; the take was retained but did not create memory.",
        )

    created, ignored_reason = create_memories_for_take(session, payload, take, project, extractor)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise IngestionError("take or memory violated a persistence constraint") from exc

    for memory in created:
        session.refresh(memory)
    session.refresh(take)
    return TakeIngestResult(
        take=TakeRead.model_validate(take),
        memories=[present_memory(memory) for memory in created],
        ignored_reason=ignored_reason,
    )


def create_memories_for_take(
    session: Session,
    payload: TakeCreate,
    take: Take,
    project: Project,
    extractor: MemoryExtractor,
) -> tuple[list[Memory], str | None]:
    extraction_result = extractor.extract(payload, project.name)

    created: list[Memory] = []
    for candidate_index, candidate in enumerate(extraction_result.decision.memories):
        text_length = len(payload.formatted_text)

        supersedes_memory_id = candidate.supersedes_memory_id
        if supersedes_memory_id is None and candidate.memory_type.value == "correction":
            matching_active = list(
                session.scalars(
                    select(Memory).where(
                        Memory.project_id == payload.project_id,
                        Memory.lifecycle_status == LifecycleStatus.ACTIVE,
                        Memory.subject == candidate.subject,
                        Memory.predicate == candidate.predicate,
                    )
                )
            )
            if len(matching_active) == 1:
                supersedes_memory_id = matching_active[0].id

        if supersedes_memory_id:
            superseded = session.get(Memory, supersedes_memory_id)
            if superseded is None:
                raise IngestionError(f"unknown supersedes_memory_id: {candidate.supersedes_memory_id}")
            if superseded.project_id != payload.project_id:
                raise IngestionError("a correction cannot supersede memory from another project")
            if (
                superseded.subject.casefold() != candidate.subject.casefold()
                or superseded.predicate.casefold() != candidate.predicate.casefold()
            ):
                raise IngestionError("a correction must match the superseded subject and predicate")
            if superseded.lifecycle_status != LifecycleStatus.ACTIVE:
                raise IngestionError("only active memory can be superseded")
            superseded.lifecycle_status = LifecycleStatus.SUPERSEDED
            superseded.valid_to = payload.event_ts

        stable_key = f"{payload.take_id}|{candidate_index}|{extraction_result.decision.schema_version}"
        memory = Memory(
            id=f"mem_{sha256(stable_key.encode('utf-8')).hexdigest()[:32]}",
            project_id=payload.project_id,
            memory_type=candidate.memory_type,
            subject=candidate.subject,
            predicate=candidate.predicate,
            object_value=candidate.object_value,
            epistemic_status=candidate.epistemic_status,
            lifecycle_status=LifecycleStatus.ACTIVE,
            valid_from=candidate.valid_from,
            valid_to=candidate.valid_to,
            confidence=candidate.confidence,
            extraction_method="model_structured_output",
            extraction_model=extraction_result.usage.model_name,
            schema_version=extraction_result.decision.schema_version,
            supersedes_memory_id=supersedes_memory_id,
        )
        for evidence in candidate.evidence:
            span_start = evidence.span_start
            span_end = evidence.span_end
            if span_start is not None and span_end is not None:
                if span_start < 0 or span_start >= text_length or span_end > text_length:
                    span_start = None
                    span_end = None
            else:
                span_start = None
                span_end = None

            memory.evidence_links.append(
                MemoryEvidence(
                    take=take,
                    span_start=span_start,
                    span_end=span_end,
                    evidence_role=evidence.role,
                    is_required=evidence.required,
                    sufficiency_contribution=evidence.sufficiency_contribution,
                )
            )
        session.add(memory)
        created.append(memory)

    return created, extraction_result.decision.ignored_reason

