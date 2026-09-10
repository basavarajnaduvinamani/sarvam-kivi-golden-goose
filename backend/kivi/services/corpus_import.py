from __future__ import annotations

from sqlalchemy.orm import Session

from ..providers import Embedder, MemoryExtractor, ProviderUnavailable
from ..schemas import CorpusImportError, CorpusImportResult, TakeCreate
from .ingestion import IngestionError, ingest_take


def import_takes(
    session: Session,
    records: list[TakeCreate],
    extractor: MemoryExtractor,
    embedder: Embedder,
) -> CorpusImportResult:
    ingested = 0
    memories_created = 0
    unscoped = 0
    errors: list[CorpusImportError] = []
    for record in records:
        try:
            result = ingest_take(session, record, extractor, embedder)
        except (IngestionError, ProviderUnavailable) as exc:
            session.rollback()
            errors.append(
                CorpusImportError(
                    take_id=record.take_id,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
            )
            continue
        ingested += 1
        memories_created += len(result.memories)
        if result.take.project_id is None:
            unscoped += 1
    return CorpusImportResult(
        total=len(records),
        ingested=ingested,
        memories_created=memories_created,
        unscoped=unscoped,
        failed=len(errors),
        errors=errors,
    )
