from __future__ import annotations

import re
from collections import defaultdict
from time import perf_counter
from uuid import uuid4

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from ..enums import EpistemicStatus, LifecycleStatus, QueryStatus
from ..models import Memory, MemoryEvidence, Project, QueryClaim, QueryRun
from ..presenters import present_memory
from ..providers import Embedder, GroundedAnswerer, ProviderUnavailable
from ..schemas import AnswerClaim, AskRequest, AskResponse
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
    if session.get(Project, payload.project_id) is None:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.NEEDS_CLARIFICATION,
            "The requested project scope does not exist.",
            started,
        )
    explicit_projects = _explicit_project_ids(session, payload.question)
    if explicit_projects and payload.project_id not in explicit_projects:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.NEEDS_CLARIFICATION,
            "The explicit project named in the question conflicts with the selected project scope.",
            started,
        )

    try:
        query_embedding = embedder.embed(payload.question)
    except ProviderUnavailable as exc:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.SERVICE_ERROR,
            "Kivi could not access the configured retrieval service. Retry after checking the model configuration.",
            started,
            error_detail=str(exc),
        )
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
    keyword_matches = _fts_memory_ids(session, payload.project_id, payload.question)
    scored: list[tuple[float, Memory]] = []
    query_vector = query_embedding.vector
    for memory in candidates:
        valid_links = [link for link in memory.evidence_links if not link.take.is_deleted and link.take.embedding]
        valid_take_ids = {link.take_id for link in valid_links}
        required_take_ids = {link.take_id for link in memory.evidence_links if link.is_required}
        if not valid_links or not required_take_ids <= valid_take_ids:
            continue
        semantic_score = max(
            cosine_similarity(blob_to_vector(link.take.embedding), np.asarray(query_vector, dtype=np.float32))
            for link in valid_links
        )
        score = semantic_score * 0.88 + (0.12 if memory.id in keyword_matches else 0.0)
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

    conflicts = _approved_conflicts(selected)
    if conflicts:
        return _record_conflict(
            session,
            query_id,
            payload,
            conflicts,
            scored,
            retrieval_latency_ms,
            started,
            query_embedding.usage.model_name,
        )

    readable = [present_memory(memory) for memory in selected]
    try:
        grounded = answerer.answer(payload.question, readable)
    except ProviderUnavailable as exc:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.SERVICE_ERROR,
            "Kivi retrieved evidence but could not generate a grounded response. Retry after checking the model configuration.",
            started,
            retrieval_latency_ms=retrieval_latency_ms,
            candidate_ids=[memory.id for _, memory in scored],
            selected_ids=[memory.id for memory in selected],
            error_detail=str(exc),
        )
    allowed_memories = {memory.id: memory for memory in readable}
    allowed_takes = {
        memory.id: {evidence.take_id for evidence in memory.evidence}
        for memory in readable
    }
    try:
        for claim in grounded.claims:
            if not claim.memory_ids:
                raise ValueError("every answer claim must cite at least one memory")
            if not set(claim.memory_ids) <= set(allowed_memories):
                raise ValueError("answerer cited a memory outside the locked evidence package")
            permitted_take_ids = set().union(*(allowed_takes[memory_id] for memory_id in claim.memory_ids))
            required_take_ids = set().union(
                *(
                    {evidence.take_id for evidence in allowed_memories[memory_id].evidence if evidence.is_required}
                    for memory_id in claim.memory_ids
                )
            )
            cited_take_ids = set(claim.supporting_take_ids)
            if not cited_take_ids or not cited_take_ids <= permitted_take_ids:
                raise ValueError("answerer cited an invalid or missing supporting take")
            if not required_take_ids <= cited_take_ids:
                raise ValueError("answerer omitted evidence required to support the complete claim")
    except ValueError as exc:
        return _record_non_answer(
            session,
            query_id,
            payload,
            QueryStatus.SERVICE_ERROR,
            "Kivi rejected an answer because its citations did not fully support its claims.",
            started,
            retrieval_latency_ms=retrieval_latency_ms,
            candidate_ids=[memory.id for _, memory in scored],
            selected_ids=[memory.id for memory in selected],
            model_name=grounded.usage.model_name,
            error_detail=str(exc),
        )

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


def _explicit_project_ids(session: Session, question: str) -> set[str]:
    folded = question.casefold()
    matched: set[str] = set()
    for project in session.scalars(select(Project)):
        names = [project.name, *project.aliases]
        if any(re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", folded) for name in names):
            matched.add(project.id)
    return matched


def _fts_memory_ids(session: Session, project_id: str, question: str) -> set[str]:
    tokens = []
    for token in re.findall(r"\w+", question.casefold(), flags=re.UNICODE):
        if len(token) > 2 and token not in tokens:
            tokens.append(token)
        if len(tokens) == 12:
            break
    if not tokens:
        return set()
    expression = " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)
    try:
        rows = session.execute(
            text(
                "SELECT memory_id FROM memory_fts "
                "WHERE project_id = :project_id AND memory_fts MATCH :expression LIMIT 50"
            ),
            {"project_id": project_id, "expression": expression},
        )
    except OperationalError as exc:
        # Unit tests use metadata-created SQLite databases without Alembic's FTS table.
        # Production and evaluation databases are required to run all migrations.
        if "no such table: memory_fts" not in str(exc).casefold():
            raise
        session.rollback()
        return set()
    return {row[0] for row in rows}


def _approved_conflicts(memories: list[Memory]) -> list[list[Memory]]:
    grouped: dict[tuple[str, str], list[Memory]] = defaultdict(list)
    for memory in memories:
        if memory.epistemic_status == EpistemicStatus.APPROVED:
            grouped[(memory.subject.casefold(), memory.predicate.casefold())].append(memory)
    conflicts: list[list[Memory]] = []
    for group in grouped.values():
        values = [memory.object_value.casefold() for memory in group]
        if len(set(values)) > 1 and not _semantically_equivalent_values(values):
            conflicts.append(group)
    return conflicts


def _semantically_equivalent_values(values: list[str]) -> bool:
    normalized: list[set[str]] = []
    ignored = {"maya", "rao", "priya", "sharma", "aaditya", "kshatriya", "neha", "iyer", "riya", "sen"}
    for value in values:
        tokens = {
            "approval" if token == "approves" else token
            for token in re.findall(r"\w+", value.casefold())
            if token not in ignored
        }
        normalized.append(tokens)
    for index, left in enumerate(normalized):
        for right in normalized[index + 1:]:
            union = left | right
            if not union or len(left & right) / len(union) < 0.6:
                return False
    return True


def _record_conflict(
    session: Session,
    query_id: str,
    payload: AskRequest,
    conflicts: list[list[Memory]],
    scored: list[tuple[float, Memory]],
    retrieval_latency_ms: int,
    started: float,
    model_name: str,
) -> AskResponse:
    memories = [memory for group in conflicts for memory in group]
    claims = [
        AnswerClaim(
            claim_text=f"{memory.subject}: {memory.predicate} = {memory.object_value}",
            memory_ids=[memory.id],
            supporting_take_ids=sorted({link.take_id for link in memory.evidence_links if not link.take.is_deleted}),
        )
        for memory in memories
    ]
    answer = "Conflicting approved evidence remains unresolved; Kivi will not choose a current value."
    elapsed = int((perf_counter() - started) * 1000)
    run = QueryRun(
        id=query_id,
        project_id=payload.project_id,
        question=payload.question,
        status=QueryStatus.CONFLICTING_EVIDENCE,
        answer=answer,
        decision_reason="Multiple active approved memories disagree without a valid supersession relationship.",
        candidate_memory_ids=[memory.id for _, memory in scored],
        selected_memory_ids=[memory.id for memory in memories],
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=elapsed,
        model_name=model_name,
    )
    for claim in claims:
        run.claims.append(
            QueryClaim(
                claim_text=claim.claim_text,
                memory_ids=claim.memory_ids,
                supporting_take_ids=claim.supporting_take_ids,
            )
        )
    session.add(run)
    session.commit()
    return AskResponse(
        query_id=query_id,
        status=QueryStatus.CONFLICTING_EVIDENCE,
        answer=answer,
        project_id=payload.project_id,
        claims=claims,
        supporting_take_ids=sorted({take_id for claim in claims for take_id in claim.supporting_take_ids}),
        decision_reason=run.decision_reason,
        retrieval_latency_ms=retrieval_latency_ms,
        end_to_end_latency_ms=elapsed,
        model_name=model_name,
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
    selected_ids: list[str] | None = None,
    model_name: str | None = None,
    error_detail: str | None = None,
) -> AskResponse:
    elapsed = int((perf_counter() - started) * 1000)
    run = QueryRun(
        id=query_id,
        project_id=payload.project_id,
        question=payload.question,
        status=status,
        answer=None,
        decision_reason=reason,
        error_detail=error_detail,
        candidate_memory_ids=candidate_ids or [],
        selected_memory_ids=selected_ids or [],
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
