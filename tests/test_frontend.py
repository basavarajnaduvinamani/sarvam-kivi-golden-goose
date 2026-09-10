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
