from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..enums import LifecycleStatus, PurgeStatus
from ..models import MemoryEvidence, Take, Tombstone, utcnow
from ..schemas import DeleteResult, TombstoneRead


class DeletionError(ValueError):
    pass


def delete_take(session: Session, take_id: str) -> DeleteResult:
    take = session.scalar(
        select(Take)
        .where(Take.id == take_id)
        .options(selectinload(Take.evidence_links).selectinload(MemoryEvidence.memory))
    )
    if take is None:
        raise DeletionError(f"unknown take_id: {take_id}")

    existing = session.get(Tombstone, take_id)
    if existing is not None:
        return DeleteResult(
            take_id=take_id,
            logically_deleted=True,
            invalidated_memory_ids=sorted(
                {link.memory_id for link in take.evidence_links if link.memory.lifecycle_status == LifecycleStatus.INVALIDATED}
            ),
            tombstone=_present_tombstone(existing),
        )

    now = utcnow()
    tombstone = Tombstone(take_id=take_id, created_at=now, purge_status=PurgeStatus.PENDING)
    take.is_deleted = True
    take.tombstoned_at = now
    invalidated_ids: list[str] = []
    for link in take.evidence_links:
        if link.memory.lifecycle_status != LifecycleStatus.TOMBSTONED:
            link.memory.lifecycle_status = LifecycleStatus.INVALIDATED
            invalidated_ids.append(link.memory_id)
    session.add(tombstone)
    session.commit()

    # Phase two is synchronous in the local demonstration. The phase-one tombstone
    # has already committed, so a purge failure cannot make the evidence queryable.
    try:
        take.raw_asr = None
        take.formatted_text = None
        take.embedding = None
        take.embedding_model = None
        take.source_metadata = {}
        tombstone.purge_status = PurgeStatus.PURGED
        tombstone.purged_at = utcnow()
        session.commit()
        _verify_exclusion(session, take_id)
        tombstone.verified_at = utcnow()
        session.commit()
    except Exception as exc:
        session.rollback()
        persisted = session.get(Tombstone, take_id)
        if persisted is not None:
            persisted.purge_status = PurgeStatus.FAILED
            persisted.failure_detail = str(exc)
            session.commit()
        raise DeletionError("logical deletion succeeded but physical purge verification failed") from exc

    session.refresh(tombstone)
    return DeleteResult(
        take_id=take_id,
        logically_deleted=True,
        invalidated_memory_ids=sorted(set(invalidated_ids)),
        tombstone=_present_tombstone(tombstone),
    )


def get_tombstone(session: Session, take_id: str) -> TombstoneRead:
    tombstone = session.get(Tombstone, take_id)
    if tombstone is None:
        raise DeletionError(f"no deletion exists for take_id: {take_id}")
    return _present_tombstone(tombstone)


def _verify_exclusion(session: Session, take_id: str) -> None:
    take = session.get(Take, take_id)
    if take is None or not take.is_deleted or take.tombstoned_at is None:
        raise DeletionError("durable logical deletion state is missing")
    if any(value is not None for value in (take.raw_asr, take.formatted_text, take.embedding, take.embedding_model)):
        raise DeletionError("purged take still contains removable content")
    active_dependency = session.scalar(
        select(MemoryEvidence.id)
        .join(MemoryEvidence.memory)
        .where(
            MemoryEvidence.take_id == take_id,
            MemoryEvidence.memory.has(lifecycle_status=LifecycleStatus.ACTIVE),
        )
        .limit(1)
    )
    if active_dependency is not None:
        raise DeletionError("an active memory still depends on the deleted take")


def _present_tombstone(tombstone: Tombstone) -> TombstoneRead:
    return TombstoneRead(
        take_id=tombstone.take_id,
        created_at=tombstone.created_at,
        purge_status=tombstone.purge_status,
        purged_at=tombstone.purged_at,
        verified_at=tombstone.verified_at,
        failure_detail=tombstone.failure_detail,
    )
