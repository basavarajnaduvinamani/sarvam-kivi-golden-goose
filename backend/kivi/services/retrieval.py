from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..enums import EpistemicStatus, LifecycleStatus, QueryStatus
from ..models import Memory, MemoryEvidence, QueryClaim, QueryRun
from ..presenters import present_memory
from ..providers import Embedder, GroundedAnswerer
from ..schemas import AskRequest, AskResponse
from ..serialization import blob_to_vector, cosine_similarity


ANSWERABLE_EPISTEMIC_STATES = {
    EpistemicStatus.APPROVED,
    EpistemicStatus.REJECTED,
    EpistemicStatus.CONDITIONAL,
    EpistemicStatus.PROPOSED,
    EpistemicStatus.UNRESOLVED,
}


def ask(
    session: Session,
    payload: AskRequest,
    embedder: Embedder,
    answerer: GroundedAnswerer,
    *,
    similarity_threshold: float = 0.45,
) -> AskResponse:
    started = perf_counter()
    query_id = f"qry_{uuid4().hex}"
    if payload.project_id is None:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.NEEDS_CLARIFICATION,
            "Project scope could not be resolved from explicit context.",
            started,
        )

    query_embedding = embedder.embed(payload.question)
    retrieval_started = perf_counter()
    statement = (
        select(Memory)
        .where(
            Memory.project_id == payload.project_id,
            Memory.lifecycle_status == LifecycleStatus.ACTIVE,
            Memory.epistemic_status.in_(ANSWERABLE_EPISTEMIC_STATES),
        )
        .options(selectinload(Memory.evidence_links).selectinload(MemoryEvidence.take))
    )
    candidates = list(session.scalars(statement))
    scored: list[tuple[float, Memory]] = []
    query_vector = query_embedding.vector
    for memory in candidates:
        valid_links = [link for link in memory.evidence_links if not link.take.is_deleted and link.take.embedding]
        if not valid_links:
            continue
        score = max(
            cosine_similarity(blob_to_vector(link.take.embedding), np.asarray(query_vector, dtype=np.float32))
            for link in valid_links
        )
        scored.append((score, memory))
    scored.sort(key=lambda item: item[0], reverse=True)
    retrieval_latency_ms = int((perf_counter() - retrieval_started) * 1000)
    selected = [memory for score, memory in scored[:5] if score >= similarity_threshold]
    if not selected:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.NO_EVIDENCE,
            "No active memory passed the project, lifecycle, evidence, and relevance gates.",
            started,
            retrieval_latency_ms=retrieval_latency_ms,
            candidate_ids=[memory.id for _, memory in scored],
            model_name=query_embedding.usage.model_name,
        )

    readable = [present_memory(memory) for memory in selected]
    grounded = answerer.answer(payload.question, readable)
    allowed_memories = {memory.id: memory for memory in readable}
    allowed_takes = {
        memory.id: {evidence.take_id for evidence in memory.evidence}
        for memory in readable
    }
    for claim in grounded.claims:
        if not claim.memory_ids:
            raise ValueError("every answer claim must cite at least one memory")
        if not set(claim.memory_ids) <= set(allowed_memories):
            raise ValueError("answerer cited a memory outside the locked evidence package")
        permitted_take_ids = set().union(*(allowed_takes[memory_id] for memory_id in claim.memory_ids))
        if not claim.supporting_take_ids or not set(claim.supporting_take_ids) <= permitted_take_ids:
            raise ValueError("answerer cited an invalid or missing supporting take")

    end_to_end_latency_ms = int((perf_counter() - started) * 1000)
    run = QueryRun(
        id=query_id,
        project_id=payload.project_id,
        question=payload.question,
        status=QueryStatus.ANSWERED,
        answer=grounded.answer,
        decision_reason="Answer generated from the locked, project-scoped evidence package.",
        candidate_memory_ids=[memory.id for _, memory in scored],
        selected_memory_ids=[memory.id for memory in selected],
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=end_to_end_latency_ms,
        model_name=grounded.usage.model_name,
        prompt_version="answer-1.0",
        input_tokens=grounded.usage.input_tokens,
        output_tokens=grounded.usage.output_tokens,
        estimated_cost_usd=grounded.usage.estimated_cost_usd,
    )
    for claim in grounded.claims:
        run.claims.append(
            QueryClaim(
                claim_text=claim.claim_text,
                memory_ids=claim.memory_ids,
                supporting_take_ids=claim.supporting_take_ids,
            )
        )
    session.add(run)
    session.commit()
    all_take_ids = sorted({take_id for claim in grounded.claims for take_id in claim.supporting_take_ids})
    return AskResponse(
        query_id=query_id,
        status=QueryStatus.ANSWERED,
        answer=grounded.answer,
        project_id=payload.project_id,
        claims=grounded.claims,
        supporting_take_ids=all_take_ids,
        decision_reason=run.decision_reason,
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=end_to_end_latency_ms,
        model_name=grounded.usage.model_name,
        input_tokens=grounded.usage.input_tokens,
        output_tokens=grounded.usage.output_tokens,
        estimated_cost_usd=grounded.usage.estimated_cost_usd,
    )


def _record_non_answer(
    session: Session,
    query_id: str,
    payload: AskRequest,
    status: QueryStatus,
    reason: str,
    started: float,
    *,
    retrieval_latency_ms: int = 0,
    candidate_ids: list[str] | None = None,
    model_name: str | None = None,
) -> AskResponse:
    elapsed = int((perf_counter() - started) * 1000)
    run = QueryRun(
        id=query_id,
        project_id=payload.project_id,
        question=payload.question,
        status=status,
        answer=None,
        decision_reason=reason,
        candidate_memory_ids=candidate_ids or [],
        selected_memory_ids=[],
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=elapsed,
        model_name=model_name,
    )
    session.add(run)
    session.commit()
    return AskResponse(
        query_id=query_id,
        status=status,
        answer=None,
        project_id=payload.project_id,
        decision_reason=reason,
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=elapsed,
        model_name=model_name,
    )
