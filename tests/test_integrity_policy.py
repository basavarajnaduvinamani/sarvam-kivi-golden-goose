from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from kivi.app import ProviderBundle, create_app
from kivi.enums import EpistemicStatus, LifecycleStatus, MemoryType, QueryStatus
from kivi.models import Memory, MemoryEvidence, Project, QueryRun, Take
from kivi.providers import GroundedAnswer, ProviderUnavailable, ProviderUsage
from kivi.schemas import AnswerClaim
from kivi.serialization import vector_to_blob

from conftest import FakeAnswerer, FakeEmbedder, FakeExtractor


class FailingEmbedder:
    def embed(self, _text):
        raise ProviderUnavailable("provider timeout with private diagnostic detail")


class UndercitingAnswerer:
    def answer(self, _question, memories):
        memory = memories[0]
        return GroundedAnswer(
            answer="An incompletely cited answer.",
            claims=[
                AnswerClaim(
                    claim_text="An incompletely cited answer.",
                    memory_ids=[memory.id],
                    supporting_take_ids=[memory.evidence[0].take_id],
                )
            ],
            usage=ProviderUsage(model_name="bad-answerer"),
        )


class FailingAnswerer:
    def answer(self, _question, _memories):
        raise ProviderUnavailable("answer service unavailable with private diagnostic detail")


def _client(session_factory, providers):
    def session_dependency():
        with session_factory() as session:
            yield session

    return TestClient(create_app(providers, session_dependency=session_dependency))


def test_retrieval_provider_failure_returns_typed_error_and_persists_diagnostic(session_factory):
    providers = ProviderBundle(
        extractor=FakeExtractor(),
        embedder=FailingEmbedder(),
        answerer=FakeAnswerer(),
    )
    with _client(session_factory, providers) as client:
        client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor"})
        response = client.post(
            "/ask",
            json={"project_id": "project-harbor", "question": "When is the release?"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SERVICE_ERROR"
    assert "private diagnostic detail" not in payload["decision_reason"]
    with session_factory() as session:
        run = session.scalar(select(QueryRun))
        assert run.status == QueryStatus.SERVICE_ERROR
        assert "private diagnostic detail" in run.error_detail


def test_answer_is_rejected_when_any_required_take_is_not_cited(session_factory):
    embedding = vector_to_blob([1.0, 1.0, 1.0])
    with session_factory() as session:
        session.add(Project(id="project-harbor", name="Project Harbor", aliases=[]))
        first = Take(
            id="take_required_1",
            project_id="project-harbor",
            raw_asr="first part",
            formatted_text="First required part.",
            source_application="Notepad",
            event_ts=datetime.now(timezone.utc),
            source_metadata={},
            embedding=embedding,
            embedding_model="fake-embedding",
        )
        second = Take(
            id="take_required_2",
            project_id="project-harbor",
            raw_asr="second part",
            formatted_text="Second required part.",
            source_application="Slack",
            event_ts=datetime.now(timezone.utc),
            source_metadata={},
            embedding=embedding,
            embedding_model="fake-embedding",
        )
        memory = Memory(
            id="mem_distributed",
            project_id="project-harbor",
            memory_type=MemoryType.DECISION,
            subject="Project Harbor",
            predicate="release readiness",
            object_value="Ready after both checks",
            epistemic_status=EpistemicStatus.APPROVED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            confidence=1.0,
            extraction_method="test",
            schema_version="1.0",
        )
        memory.evidence_links.extend(
            [
                MemoryEvidence(take=first, span_start=0, span_end=19, is_required=True),
                MemoryEvidence(take=second, span_start=0, span_end=20, is_required=True),
            ]
        )
        session.add(memory)
        session.commit()

    providers = ProviderBundle(
        extractor=FakeExtractor(),
        embedder=FakeEmbedder(),
        answerer=UndercitingAnswerer(),
    )
    with _client(session_factory, providers) as client:
        response = client.post(
            "/ask",
            json={"project_id": "project-harbor", "question": "Is Harbor ready?"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "SERVICE_ERROR"
    assert "citations did not fully support" in response.json()["decision_reason"]


def test_answer_provider_failure_persists_selected_evidence_without_leaking_diagnostic(client, session_factory):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor"})
    content = "Project Harbor's release is Thursday at 4 PM."
    ingested = client.post(
        "/takes",
        json={
            "take_id": "take_answer_failure",
            "project_id": "project-harbor",
            "raw_asr": content.lower(),
            "formatted_text": content,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        },
    ).json()
    memory_id = ingested["memories"][0]["id"]
    providers = ProviderBundle(extractor=FakeExtractor(), embedder=FakeEmbedder(), answerer=FailingAnswerer())
    with _client(session_factory, providers) as failing_client:
        response = failing_client.post(
            "/ask",
            json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SERVICE_ERROR"
    assert "private diagnostic detail" not in payload["decision_reason"]
    with session_factory() as session:
        run = session.scalar(select(QueryRun).order_by(QueryRun.created_at.desc()))
        assert run.selected_memory_ids == [memory_id]
        assert "private diagnostic detail" in run.error_detail
