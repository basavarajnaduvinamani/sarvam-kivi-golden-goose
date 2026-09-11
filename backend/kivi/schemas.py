from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import EpistemicStatus, LifecycleStatus, MemoryType, PurgeStatus, QueryStatus


class ProjectCreate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,99}$")
    name: str = Field(min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    updated_at: datetime


class TakeCreate(BaseModel):
    take_id: str = Field(min_length=1, max_length=100)
    raw_asr: str = Field(min_length=1)
    formatted_text: str = Field(min_length=1)
    source_application: str = Field(min_length=1, max_length=100)
    event_ts: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def resolve_project_field(self) -> TakeCreate:
        metadata_project = self.metadata.get("project_id")
        if self.project_id and metadata_project and self.project_id != metadata_project:
            raise ValueError("project_id conflicts with metadata.project_id")
        if self.project_id is None and isinstance(metadata_project, str):
            self.project_id = metadata_project
        return self


class TakeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str | None
    raw_asr: str | None
    formatted_text: str | None
    source_application: str
    event_ts: datetime
    ingested_ts: datetime
    source_metadata: dict[str, Any]
    embedding_model: str | None
    is_deleted: bool
    tombstoned_at: datetime | None


class EvidenceCandidate(BaseModel):
    span_start: int | None = Field(default=None, ge=0)
    span_end: int | None = Field(default=None, ge=0)
    role: str = "supporting"
    required: bool = True
    sufficiency_contribution: str | None = None

    @model_validator(mode="after")
    def valid_span(self) -> EvidenceCandidate:
        if (self.span_start is None) != (self.span_end is None):
            raise ValueError("span_start and span_end must be supplied together")
        if self.span_start is not None and self.span_end <= self.span_start:
            raise ValueError("span_end must be greater than span_start")
        return self


class MemoryCandidate(BaseModel):
    memory_type: MemoryType
    subject: str = Field(min_length=1, max_length=300)
    predicate: str = Field(min_length=1, max_length=200)
    object_value: str = Field(min_length=1)
    epistemic_status: EpistemicStatus
    confidence: float = Field(ge=0, le=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    supersedes_memory_id: str | None = None
    evidence: list[EvidenceCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def require_sufficient_evidence(self) -> MemoryCandidate:
        if not any(item.required for item in self.evidence):
            raise ValueError("every memory requires at least one required evidence span")
        return self


class ExtractionDecision(BaseModel):
    schema_version: str = "1.0"
    memories: list[MemoryCandidate] = Field(default_factory=list)
    ignored_reason: str | None = None

    @model_validator(mode="after")
    def explain_empty_result(self) -> ExtractionDecision:
        if not self.memories and not self.ignored_reason:
            raise ValueError("an extraction with no memories must explain why it was ignored")
        return self


class MemoryEvidenceRead(BaseModel):
    take_id: str
    span_start: int | None
    span_end: int | None
    evidence_role: str
    is_required: bool
    sufficiency_contribution: str | None


class MemoryRead(BaseModel):
    id: str
    project_id: str
    memory_type: MemoryType
    subject: str
    predicate: str
    object_value: str
    epistemic_status: EpistemicStatus
    lifecycle_status: LifecycleStatus
    valid_from: datetime | None
    valid_to: datetime | None
    confidence: float
    extraction_method: str
    extraction_model: str | None
    schema_version: str
    supersedes_memory_id: str | None
    evidence: list[MemoryEvidenceRead]


class TakeIngestResult(BaseModel):
    take: TakeRead
    memories: list[MemoryRead]
    ignored_reason: str | None = None


class TakeScopeAssignmentRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)


class MemoryCorrectionRequest(BaseModel):
    corrected_value: str = Field(min_length=1)
    note: str | None = Field(default=None, max_length=1000)


class CorpusImportError(BaseModel):
    take_id: str
    error_type: str
    detail: str


class CorpusImportResult(BaseModel):
    total: int = Field(ge=0)
    ingested: int = Field(ge=0)
    memories_created: int = Field(ge=0)
    unscoped: int = Field(ge=0)
    failed: int = Field(ge=0)
    errors: list[CorpusImportError] = Field(default_factory=list)


class AskRequest(BaseModel):
    project_id: str | None = Field(default=None, max_length=100)
    question: str = Field(min_length=1)


class AnswerClaim(BaseModel):
    claim_text: str
    memory_ids: list[str]
    supporting_take_ids: list[str]


class AskResponse(BaseModel):
    query_id: str
    status: QueryStatus
    answer: str | None
    project_id: str | None
    claims: list[AnswerClaim] = Field(default_factory=list)
    supporting_take_ids: list[str] = Field(default_factory=list)
    decision_reason: str
    retrieval_latency_ms: int = Field(ge=0)
    end_to_end_latency_ms: int = Field(ge=0)
    model_name: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class TombstoneRead(BaseModel):
    take_id: str
    created_at: datetime
    purge_status: PurgeStatus
    purged_at: datetime | None
    verified_at: datetime | None
    failure_detail: str | None


class DeleteResult(BaseModel):
    take_id: str
    logically_deleted: bool
    invalidated_memory_ids: list[str]
    tombstone: TombstoneRead


class BriefingRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)
    focus: str = Field(
        default="Provide the current project state, including decisions, constraints, commitments, and unresolved items.",
        min_length=1,
    )


class TimelineEvidenceRead(BaseModel):
    take_id: str
    source_application: str
    event_ts: datetime
    span_start: int | None
    span_end: int | None
    evidence_role: str
    is_required: bool
    is_deleted: bool


class TimelineEntryRead(BaseModel):
    memory_id: str
    memory_type: MemoryType
    subject: str
    predicate: str
    object_value: str
    epistemic_status: EpistemicStatus
    lifecycle_status: LifecycleStatus
    valid_from: datetime | None
    valid_to: datetime | None
    created_at: datetime
    supersedes_memory_id: str | None
    superseded_by_memory_ids: list[str] = Field(default_factory=list)
    evidence: list[TimelineEvidenceRead]


class ProjectTimelineResponse(BaseModel):
    project: ProjectRead
    entries: list[TimelineEntryRead]


class EvaluationRunRequest(BaseModel):
    mode: Literal["deterministic", "candidate"] = "deterministic"


class EvaluationCaseResultRead(BaseModel):
    case_id: str
    category: str
    description: str
    project_id: str | None
    question: str
    expected_status: QueryStatus
    actual_status: QueryStatus
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    relevant_memory_ids: list[str] = Field(default_factory=list)
    supporting_take_ids: list[str] = Field(default_factory=list)
    duration_ms: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class EvaluationCategoryMetrics(BaseModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)


class EvaluationMetricsRead(BaseModel):
    total_cases: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    answer_correctness: float = Field(ge=0, le=1)
    abstention_precision: float = Field(ge=0, le=1)
    abstention_recall: float = Field(ge=0, le=1)
    conflict_detection_accuracy: float = Field(ge=0, le=1)
    project_scope_accuracy: float = Field(ge=0, le=1)
    decision_status_accuracy: float = Field(ge=0, le=1)
    temporal_correction_accuracy: float = Field(ge=0, le=1)
    provenance_coverage: float = Field(ge=0, le=1)
    deletion_integrity: float = Field(ge=0, le=1)
    cross_project_leakage_count: int = Field(ge=0)
    deleted_memory_resurrection_count: int = Field(ge=0)
    invalid_citation_count: int = Field(ge=0)
    rejected_proposal_promotion_count: int = Field(ge=0)
    fabricated_answer_count: int = Field(ge=0)
    retrieval_latency_p50_ms: float = Field(ge=0)
    retrieval_latency_p95_ms: float = Field(ge=0)
    end_to_end_latency_p50_ms: float = Field(ge=0)
    end_to_end_latency_p95_ms: float = Field(ge=0)
    database_bytes_before: int = Field(ge=0)
    database_bytes_after: int = Field(ge=0)
    database_growth_bytes: int
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    by_category: dict[str, EvaluationCategoryMetrics] = Field(default_factory=dict)


class EvaluationRunRead(BaseModel):
    run_id: str
    mode: Literal["deterministic", "candidate"]
    started_at: datetime
    completed_at: datetime
    corpus_record_count: int = Field(ge=0)
    case_count: int = Field(ge=0)
    metrics: EvaluationMetricsRead
    cases: list[EvaluationCaseResultRead]
    results_json_path: str
    report_markdown_path: str

