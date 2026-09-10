from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .enums import EpistemicStatus, LifecycleStatus, MemoryType, PurgeStatus, QueryStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    takes: Mapped[list[Take]] = relationship(back_populates="project")
    memories: Mapped[list[Memory]] = relationship(back_populates="project")


class Take(Base):
    __tablename__ = "takes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    raw_asr: Mapped[str | None] = mapped_column(Text)
    formatted_text: Mapped[str | None] = mapped_column(Text)
    source_application: Mapped[str] = mapped_column(String(100), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project | None] = relationship(back_populates="takes")
    evidence_links: Mapped[list[MemoryEvidence]] = relationship(back_populates="take")
    tombstone: Mapped[Tombstone | None] = relationship(back_populates="take", uselist=False)


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_project_lifecycle", "project_id", "lifecycle_status"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    memory_type: Mapped[MemoryType] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    predicate: Mapped[str] = mapped_column(String(200), nullable=False)
    object_value: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_status: Mapped[EpistemicStatus] = mapped_column(String(30), nullable=False)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(String(30), default=LifecycleStatus.ACTIVE, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    extraction_model: Mapped[str | None] = mapped_column(String(200))
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    supersedes_memory_id: Mapped[str | None] = mapped_column(ForeignKey("memories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped[Project] = relationship(back_populates="memories")
    evidence_links: Mapped[list[MemoryEvidence]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    supersedes: Mapped[Memory | None] = relationship(remote_side=[id])


class MemoryEvidence(Base):
    __tablename__ = "memory_evidence"
    __table_args__ = (
        UniqueConstraint("memory_id", "take_id", "span_start", "span_end", name="uq_memory_evidence_span"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False, index=True)
    take_id: Mapped[str] = mapped_column(ForeignKey("takes.id"), nullable=False, index=True)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    evidence_role: Mapped[str] = mapped_column(String(50), default="supporting", nullable=False)
    sufficiency_contribution: Mapped[str | None] = mapped_column(Text)

    memory: Mapped[Memory] = relationship(back_populates="evidence_links")
    take: Mapped[Take] = relationship(back_populates="evidence_links")


class Tombstone(Base):
    __tablename__ = "tombstones"

    take_id: Mapped[str] = mapped_column(ForeignKey("takes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    purge_status: Mapped[PurgeStatus] = mapped_column(String(20), default=PurgeStatus.PENDING, nullable=False)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_detail: Mapped[str | None] = mapped_column(Text)

    take: Mapped[Take] = relationship(back_populates="tombstone")


class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[QueryStatus] = mapped_column(String(40), nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    selected_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retrieval_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_to_end_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    claims: Mapped[list[QueryClaim]] = relationship(back_populates="query_run", cascade="all, delete-orphan")


class QueryClaim(Base):
    __tablename__ = "query_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_run_id: Mapped[str] = mapped_column(ForeignKey("query_runs.id"), nullable=False, index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    supporting_take_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    query_run: Mapped[QueryRun] = relationship(back_populates="claims")

