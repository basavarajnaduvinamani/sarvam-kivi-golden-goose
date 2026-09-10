import pytest
from fastapi.testclient import TestClient
from backend.kivi.main import app
from backend.kivi.app import ProviderBundle, create_app
from backend.kivi.schemas import AskResponse, TakeRead
from backend.kivi.providers import MemoryExtractor, Embedder, GroundedAnswerer, EmbeddingResult, ProviderUsage
from backend.kivi.db import get_session
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from backend.kivi.models import Base, Take, Project
from datetime import datetime, timezone

class MockExtractor(MemoryExtractor):
    def extract(self, take_text, project_context):
        return []

class MockEmbedder(Embedder):
    def embed(self, text):
        return EmbeddingResult(vector=[0.0] * 1536, usage=ProviderUsage(model_name="mock"))

class MockAnswerer(GroundedAnswerer):
    def __init__(self, mock_response: AskResponse):
        self.mock_response = mock_response

    def answer(self, question, project_id, evidence):
        return self.mock_response

from sqlalchemy.pool import StaticPool

@pytest.fixture
def mock_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Create a mock project
        p = Project(id="test-project", name="Test Project", aliases=["TP"])
        # Create a mock take
        t = Take(
            id="take_123",
            project_id="test-project",
            raw_asr="raw text",
            formatted_text="formatted text",
            source_application="Terminal",
            event_ts=datetime.now(timezone.utc),
            embedding_model="mock",
            is_deleted=False
        )
        session.add(p)
        session.add(t)
        session.commit()
        yield session

def override_get_session(session):
    def _override():
        yield session
    return _override

from unittest.mock import patch

def create_test_app():
    from frontend.router import router as frontend_router
    test_app = create_app(providers=ProviderBundle(
        extractor=MockExtractor(),
        embedder=MockEmbedder(),
        answerer=None
    ))
    test_app.include_router(frontend_router)
    return test_app

def test_app_boots_without_openai():
    # Prove the app boots without a key
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

def test_get_index(mock_session):
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Kivi" in response.text
    assert "Test Project" in response.text # Project selector populated

@patch('frontend.router.ask')
def test_ask_answered(mock_ask, mock_session):
    mock_ask.return_value = AskResponse(
        query_id="q1",
        status="ANSWERED",
        answer="This is the answer.",
        project_id="test-project",
        claims=[{
            "claim_text": "This is a claim.",
            "memory_ids": ["m1"],
            "supporting_take_ids": ["take_123"]
        }],
        supporting_take_ids=["take_123"],
        decision_reason="Testing",
        retrieval_latency_ms=5,
        end_to_end_latency_ms=10
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)

    response = client.post("/htmx/ask", data={"question": "Hello?", "project_id": "test-project"})
    assert response.status_code == 200
    html = response.text
    assert "This is the answer." in html
    assert "This is a claim." in html
    assert "take_123" in html
    assert 'hx-get="/htmx/takes/take_123"' in html

@patch('frontend.router.ask')
def test_ask_no_evidence(mock_ask, mock_session):
    mock_ask.return_value = AskResponse(
        query_id="q2",
        status="NO_EVIDENCE",
        answer=None,
        project_id="test-project",
        claims=[],
        supporting_take_ids=[],
        decision_reason="No evidence",
        retrieval_latency_ms=5,
        end_to_end_latency_ms=10
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)

    response = client.post("/htmx/ask", data={"question": "Hello?"})
    assert response.status_code == 200
    assert "NO EVIDENCE" in response.text
    assert "valid, project-scoped evidence" in response.text
    assert "null" not in response.text

@patch('frontend.router.ask')
def test_ask_needs_clarification(mock_ask, mock_session):
    mock_ask.return_value = AskResponse(
        query_id="q3",
        status="NEEDS_CLARIFICATION",
        answer=None,
        project_id=None,
        claims=[],
        supporting_take_ids=[],
        decision_reason="Ambiguous",
        retrieval_latency_ms=5,
        end_to_end_latency_ms=10
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)

    response = client.post("/htmx/ask", data={"question": "Hello?"})
    assert response.status_code == 200
    assert "NEEDS CLARIFICATION" in response.text

@patch('frontend.router.ask')
def test_ask_conflicting_evidence(mock_ask, mock_session):
    mock_ask.return_value = AskResponse(
        query_id="q4",
        status="CONFLICTING_EVIDENCE",
        answer="I have conflicting info.",
        project_id="test-project",
        claims=[
            {"claim_text": "Claim A", "memory_ids": ["m1"], "supporting_take_ids": ["t1"]},
            {"claim_text": "Claim B", "memory_ids": ["m2"], "supporting_take_ids": ["t2"]}
        ],
        supporting_take_ids=["t1", "t2"],
        decision_reason="Conflict",
        retrieval_latency_ms=5,
        end_to_end_latency_ms=10
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)

    response = client.post("/htmx/ask", data={"question": "Hello?"})
    assert response.status_code == 200
    assert "CONFLICTING EVIDENCE" in response.text
    assert "Claim A" in response.text
    assert "Claim B" in response.text

@patch('frontend.router.ask')
def test_ask_service_error(mock_ask):
    mock_ask.side_effect = Exception("Database is down")
    client = TestClient(app)
    response = client.post("/htmx/ask", data={"question": "Hello?"})
    assert response.status_code == 200
    assert "SERVICE ERROR" in response.text

def test_evidence_drawer_loads_take(mock_session):
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    response = client.get("/htmx/takes/take_123")
    assert response.status_code == 200
    assert "formatted text" in response.text
    assert "ACTIVE" in response.text

def test_evidence_drawer_missing_take(mock_session):
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    response = client.get("/htmx/takes/take_invalid")
    assert response.status_code == 200
    assert "Evidence not found" in response.text

def test_index_form_behavior():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Ensure destructive pre-serialization onsubmit handler is absent
    assert "onsubmit=" not in html
    # Ensure the question clears only after the HTMX request completes
    assert "hx-on::after-request" in html
    assert "if (event.detail.successful)" in html
    assert "document.getElementById('question-input').value = ''" in html

def test_favicon_route_and_reference():
    client = TestClient(app)

    # Base template references the local favicon
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/static/favicon.svg"' in response.text

    # The local favicon route returns 200
    favicon_response = client.get("/static/favicon.svg")
    assert favicon_response.status_code == 200
    assert "svg" in favicon_response.headers.get("content-type", "")


def test_timeline_page_loads():
    client = TestClient(app)
    response = client.get("/timeline")
    assert response.status_code == 200
    assert "Project Memory Timeline" in response.text

@patch('frontend.router.get_project_timeline')
def test_htmx_timeline_success(mock_get_timeline, mock_session):
    from backend.kivi.schemas import ProjectTimelineResponse, ProjectRead, TimelineEntryRead, TimelineEvidenceRead
    from datetime import datetime, timezone
    mock_get_timeline.return_value = ProjectTimelineResponse(
        project=ProjectRead(id="test-project", name="Test Project", aliases=[], created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)),
        entries=[
            TimelineEntryRead(
                memory_id="mem1",
                memory_type="decision",
                subject="User",
                predicate="likes",
                object_value="apples",
                epistemic_status="APPROVED",
                lifecycle_status="ACTIVE",
                valid_from=None,
                valid_to=None,
                created_at=datetime.now(timezone.utc),
                supersedes_memory_id=None,
                superseded_by_memory_ids=[],
                evidence=[
                    TimelineEvidenceRead(
                        take_id="take_123",
                        source_application="Terminal",
                        event_ts=datetime.now(timezone.utc),
                        span_start=0,
                        span_end=10,
                        evidence_role="supporting",
                        is_required=True,
                        is_deleted=False
                    )
                ]
            )
        ]
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    response = client.get("/htmx/timeline/test-project")
    assert response.status_code == 200
    assert "Timeline for Test Project" in response.text
    assert "apples" in response.text
    assert "Revoke" in response.text

def test_import_eval_page_loads():
    client = TestClient(app)
    response = client.get("/import-eval")
    assert response.status_code == 200
    assert "Import Corpus" in response.text
    assert "Evaluation Dashboard" in response.text

@patch('frontend.router.import_takes')
def test_htmx_import_success(mock_import_takes, mock_session):
    from backend.kivi.schemas import CorpusImportResult
    mock_import_takes.return_value = CorpusImportResult(
        total=1, ingested=1, memories_created=1, unscoped=0, failed=0, errors=[]
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    
    files = {"corpus_file": ("test.jsonl", b'[{"take_id": "test1", "project_id": "test-project", "raw_asr": "hi", "formatted_text": "hi", "source_application": "Test", "event_ts": "2026-09-10T09:30:00Z"}]', "application/json")}
    response = client.post("/htmx/import", files=files)
    assert response.status_code == 200
    assert "Import Successful" in response.text
    assert "Successfully Ingested:</strong> 1" in response.text

def test_htmx_evaluate_latest_mock():
    test_app = create_test_app()
    from backend.kivi.schemas import EvaluationRunRead, EvaluationMetricsRead
    from datetime import datetime, timezone
    mock_metrics = EvaluationMetricsRead(
        total_cases=10, passed=10, failed=0, pass_rate=1.0,
        answer_correctness=1.0, abstention_precision=1.0, abstention_recall=1.0,
        conflict_detection_accuracy=1.0, project_scope_accuracy=1.0,
        decision_status_accuracy=1.0, temporal_correction_accuracy=1.0,
        provenance_coverage=1.0, deletion_integrity=1.0,
        cross_project_leakage_count=0, deleted_memory_resurrection_count=0,
        invalid_citation_count=0, rejected_proposal_promotion_count=0,
        fabricated_answer_count=0, retrieval_latency_p50_ms=10.0,
        retrieval_latency_p95_ms=20.0, end_to_end_latency_p50_ms=50.0,
        end_to_end_latency_p95_ms=100.0, database_bytes_before=100,
        database_bytes_after=200, database_growth_bytes=100,
        input_tokens=1000, output_tokens=500, estimated_cost_usd=0.01,
        by_category={}
    )
    test_app.state.mock_evaluation_run = EvaluationRunRead(
        run_id="run_123",
        mode="deterministic",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        corpus_record_count=500,
        case_count=10,
        metrics=mock_metrics,
        cases=[],
        results_json_path="test.json",
        report_markdown_path="test.md"
    )
    client = TestClient(test_app)
    response = client.get("/htmx/evaluate/latest")
    assert response.status_code == 200
    assert "Run ID: run_123" in response.text
    assert "Pass Rate:</strong> 100.0%" in response.text

@patch('frontend.router.delete_take')
def test_htmx_revoke_take(mock_delete, mock_session):
    from backend.kivi.schemas import DeleteResult, TombstoneRead
    from datetime import datetime, timezone
    mock_delete.return_value = DeleteResult(
        take_id="take_123",
        logically_deleted=True,
        invalidated_memory_ids=["mem1"],
        tombstone=TombstoneRead(
            take_id="take_123",
            created_at=datetime.now(timezone.utc),
            purge_status="pending",
            purged_at=None,
            verified_at=None,
            failure_detail=None
        )
    )
    test_app = create_test_app()
    test_app.dependency_overrides[get_session] = override_get_session(mock_session)
    client = TestClient(test_app)
    response = client.delete("/htmx/takes/take_123")
    assert response.status_code == 200
    assert "Revoked successfully!" in response.text

