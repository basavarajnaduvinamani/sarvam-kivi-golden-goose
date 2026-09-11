from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..enums import EpistemicStatus, LifecycleStatus, MemoryType
from ..models import Memory, MemoryEvidence, Project, Take, utcnow
from ..presenters import present_memory
from ..providers import Embedder, MemoryExtractor
from ..schemas import (
    MemoryCorrectionRequest,
    TakeCreate,
    TakeIngestResult,
    TakeRead,
    TakeScopeAssignmentRequest,
)
from ..serialization import vector_to_blob
from .ingestion import create_memories_for_take


class MemoryControlError(ValueError):
    pass


def assign_take_scope(
    session: Session,
    take_id: str,
    payload: TakeScopeAssignmentRequest,
    extractor: MemoryExtractor,
) -> TakeIngestResult:
    take = session.get(Take, take_id)
    if take is None:
        raise MemoryControlError("take not found")
    if take.is_deleted:
        raise MemoryControlError("deleted take cannot be assigned to a project")
    if take.project_id is not None:
        raise MemoryControlError("take already has confirmed project scope")
    project = session.get(Project, payload.project_id)
    if project is None:
        raise MemoryControlError(f"unknown project_id: {payload.project_id}")
    if take.raw_asr is None or take.formatted_text is None:
        raise MemoryControlError("purged take cannot create memory")

    take.project_id = project.id
    source = TakeCreate(
        take_id=take.id,
        project_id=project.id,
        raw_asr=take.raw_asr,
        formatted_text=take.formatted_text,
        source_application=take.source_application,
        event_ts=take.event_ts,
        metadata=take.source_metadata,
    )
    try:
        created, ignored_reason = create_memories_for_take(session, source, take, project, extractor)
        session.commit()
    except Exception:
        session.rollback()
        raise

    session.refresh(take)
    for memory in created:
        session.refresh(memory)
    return TakeIngestResult(
        take=TakeRead.model_validate(take),
        memories=[present_memory(memory) for memory in created],
        ignored_reason=ignored_reason,
    )


def correct_memory(
    session: Session,
    memory_id: str,
    payload: MemoryCorrectionRequest,
    embedder: Embedder,
) -> TakeIngestResult:
    original = session.scalar(
        select(Memory)
        .where(Memory.id == memory_id)
        .options(selectinload(Memory.evidence_links))
    )
    if original is None:
        raise MemoryControlError("memory not found")
    if original.lifecycle_status != LifecycleStatus.ACTIVE:
        raise MemoryControlError("only active memory can be corrected")

    corrected_value = payload.corrected_value.strip()
    if not corrected_value:
        raise MemoryControlError("corrected value cannot be blank")
    now = utcnow()
    take_id = f"take_correction_{uuid4().hex}"
    correction_text = f"Correction for {original.subject}: {original.predicate} is {corrected_value}."
    if payload.note and payload.note.strip():
        correction_text += f" Note: {payload.note.strip()}"
    embedding_result = embedder.embed(correction_text)
    take = Take(
        id=take_id,
        project_id=original.project_id,
        raw_asr=correction_text,
        formatted_text=correction_text,
        source_application="Kivi Memory Inspector",
        event_ts=now,
        source_metadata={
            "action": "user_confirmed_correction",
            "corrected_memory_id": original.id,
            "note": payload.note,
        },
        embedding=vector_to_blob(embedding_result.vector),
        embedding_model=embedding_result.usage.model_name,
    )
    stable_key = f"{take_id}|0|1.0"
    corrected = Memory(
        id=f"mem_{sha256(stable_key.encode('utf-8')).hexdigest()[:32]}",
        project_id=original.project_id,
        memory_type=MemoryType.CORRECTION,
        subject=original.subject,
        predicate=original.predicate,
        object_value=corrected_value,
        epistemic_status=EpistemicStatus.APPROVED,
        lifecycle_status=LifecycleStatus.ACTIVE,
        valid_from=now,
        valid_to=None,
        confidence=1.0,
        extraction_method="user_confirmed_correction",
        extraction_model=None,
        schema_version="1.0",
        supersedes_memory_id=original.id,
    )
    corrected.evidence_links.append(
        MemoryEvidence(
            take=take,
            span_start=0,
            span_end=len(correction_text),
            evidence_role="user_correction",
            is_required=True,
            sufficiency_contribution="The user explicitly confirmed the replacement value.",
        )
    )
    original.lifecycle_status = LifecycleStatus.SUPERSEDED
    original.valid_to = now
    session.add_all([take, corrected])
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    session.refresh(take)
    session.refresh(corrected)
    return TakeIngestResult(
        take=TakeRead.model_validate(take),
        memories=[present_memory(corrected)],
    )
