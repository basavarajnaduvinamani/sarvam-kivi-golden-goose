from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from kivi.app import ProviderBundle, create_app
from kivi.db import Base
from kivi.enums import EpistemicStatus, MemoryType
from kivi.providers import EmbeddingResult, ExtractionResult, GroundedAnswer, ProviderUsage
from kivi.schemas import AnswerClaim, EvidenceCandidate, ExtractionDecision, MemoryCandidate


class FakeEmbedder:
    def embed(self, text: str) -> EmbeddingResult:
        lowered = text.lower()
        vector = [
            float("harbor" in lowered),
            float("release" in lowered or "plan" in lowered),
            float("thursday" in lowered or "when" in lowered),
        ]
        if not any(vector):
            vector = [0.01, 0.01, 0.01]
        return EmbeddingResult(vector=vector, usage=ProviderUsage(model_name="fake-embedding"))


class FakeExtractor:
    def extract(self, take, project_name: str) -> ExtractionResult:
        text = take.formatted_text
        object_value = take.metadata.get("object_value", "Thursday at 4 PM")
        return ExtractionResult(
            decision=ExtractionDecision(
                memories=[
                    MemoryCandidate(
                        memory_type=MemoryType.DECISION,
                        subject=project_name,
                        predicate="release schedule",
                        object_value=object_value,
                        epistemic_status=EpistemicStatus.APPROVED,
                        confidence=0.99,
                        supersedes_memory_id=take.metadata.get("supersedes_memory_id"),
                        evidence=[EvidenceCandidate(span_start=0, span_end=len(text))],
                    )
                ]
            ),
            usage=ProviderUsage(model_name="fake-extractor"),
        )


class FakeAnswerer:
    def answer(self, question, memories):
        memory = memories[0]
        take_ids = [evidence.take_id for evidence in memory.evidence]
        claim = f"{memory.subject}'s {memory.predicate} is {memory.object_value}."
        return GroundedAnswer(
            answer=claim,
            claims=[AnswerClaim(claim_text=claim, memory_ids=[memory.id], supporting_take_ids=take_ids)],
            usage=ProviderUsage(model_name="fake-answerer"),
        )


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:
    def session_dependency():
        with session_factory() as session:
            yield session

    app = create_app(
        ProviderBundle(
            extractor=FakeExtractor(),
            embedder=FakeEmbedder(),
            answerer=FakeAnswerer(),
        ),
        session_dependency=session_dependency,
    )
    with TestClient(app) as test_client:
        yield test_client

