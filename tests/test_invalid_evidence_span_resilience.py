from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from kivi.db import Base
from kivi.enums import EpistemicStatus, MemoryType
from kivi.models import Project
from kivi.providers import EmbeddingResult, ExtractionResult, ProviderUsage
from kivi.schemas import (
    EvidenceCandidate,
    ExtractionDecision,
    MemoryCandidate,
    TakeCreate,
)
from kivi.services.ingestion import ingest_take


class FakeEmbedder:
    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            usage=ProviderUsage(model_name="fake-embedder"),
        )


class FakeSpanExceedingExtractor:
    """Extractor returning an evidence span where span_end exceeds formatted_text length by 1."""

    def extract(self, take: TakeCreate, project_name: str) -> ExtractionResult:
        text_len = len(take.formatted_text)
        return ExtractionResult(
            decision=ExtractionDecision(
                memories=[
                    MemoryCandidate(
                        memory_type=MemoryType.DECISION,
                        subject="client SDK release",
                        predicate="is frozen until",
                        object_value="next Wednesday",
                        epistemic_status=EpistemicStatus.APPROVED,
                        confidence=0.95,
                        supersedes_memory_id=None,
                        evidence=[
                            EvidenceCandidate(
                                span_start=12,
                                span_end=text_len + 1,  # Exceeds len(formatted_text) by 1
                                role="supporting",
                                required=True,
                                sufficiency_contribution="full",
                            )
                        ],
                    )
                ]
            ),
            usage=ProviderUsage(model_name="fake-extractor"),
        )


def test_invalid_evidence_span_resilience_preserves_take_provenance():
    # Setup in-memory database with test project
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        project = Project(
            id="proj-alpha",
            name="Project Alpha",
            aliases=["Alpha"],
        )
        session.add(project)
        session.commit()

        # Code-switched Indic-English text (length 102 characters)
        formatted_text = "Arre suno, hamne decide kiya hai ki client SDK release next Wednesday tak freeze rahegi, bilkul pakka."
        assert len(formatted_text) == 102

        payload = TakeCreate(
            take_id="take_indic_001",
            project_id="proj-alpha",
            raw_asr="arre suno hamne decide kiya hai ki client sdk release next wednesday tak freeze rahegi bilkul pakka",
            formatted_text=formatted_text,
            source_application="Voice Note",
            event_ts=datetime(2026, 9, 12, 11, 15, 0, tzinfo=timezone.utc),
            metadata={},
        )

        extractor = FakeSpanExceedingExtractor()
        embedder = FakeEmbedder()

        # Ingestion must succeed without raising IngestionError
        result = ingest_take(session, payload, extractor, embedder)

        assert result.take.id == "take_indic_001"
        assert len(result.memories) == 1

        created_memory = result.memories[0]
        assert created_memory.project_id == "proj-alpha"
        assert created_memory.subject == "client SDK release"
        assert created_memory.predicate == "is frozen until"
        assert created_memory.object_value == "next Wednesday"
        assert created_memory.epistemic_status == EpistemicStatus.APPROVED

        # The supporting Take provenance link MUST exist
        assert len(created_memory.evidence) == 1
        evidence_link = created_memory.evidence[0]
        assert evidence_link.take_id == "take_indic_001"
        assert evidence_link.evidence_role == "supporting"
        assert evidence_link.is_required is True

        # Out-of-bounds span must be safely nulled out (None / null), not clamped or fabricated
        assert evidence_link.span_start is None
        assert evidence_link.span_end is None
