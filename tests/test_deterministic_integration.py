import json
import pytest
from fastapi.testclient import TestClient
from backend.kivi.app import create_app, default_provider_bundle
from backend.kivi.db import get_session
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from backend.kivi.models import Base, Project
from sqlalchemy.pool import StaticPool
from backend.kivi.evaluation.providers import GoldExtractor, DeterministicEmbedder, DeterministicAnswerer
from backend.kivi.settings import get_settings

@pytest.fixture
def test_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(id="project-harbor", name="Project Harbor", aliases=["Harbor"])
        session.add(project)
        session.commit()
        yield session

def override_get_session(session):
    def _override():
        yield session
    return _override

def test_deterministic_provider_selection(monkeypatch):
    monkeypatch.setenv("KIVI_MODEL_PROVIDER", "deterministic")
    get_settings.cache_clear()
    try:
        bundle = default_provider_bundle()
        assert isinstance(bundle.extractor, GoldExtractor)
        assert isinstance(bundle.embedder, DeterministicEmbedder)
        assert isinstance(bundle.answerer, DeterministicAnswerer)
    finally:
        get_settings.cache_clear()

def test_deterministic_corpus_and_endpoints(monkeypatch, test_db_session):
    monkeypatch.setenv("KIVI_MODEL_PROVIDER", "deterministic")
    get_settings.cache_clear()
    try:
        bundle = default_provider_bundle()
        app = create_app(providers=bundle)
        app.dependency_overrides[get_session] = override_get_session(test_db_session)
        client = TestClient(app)

        take_0001_payload = None
        with open("corpus/kivi_500.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                if record.get("take_id") == "take_0001":
                    take_0001_payload = record
                    break
        assert take_0001_payload is not None, "take_0001 not found in corpus"

        res_ingest = client.post("/takes", json=take_0001_payload)
        assert res_ingest.status_code == 201
        assert len(res_ingest.json()["memories"]) >= 1

        ask_payload = {"question": "Who owns the payment recovery workstream for Project Harbor?", "project_id": "project-harbor"}
        res_ask = client.post("/ask", json=ask_payload)
        assert res_ask.status_code == 200
        ask_data = res_ask.json()
        assert ask_data["status"] == "ANSWERED", f"Expected ANSWERED, got {ask_data['status']}. Response: {ask_data}"
        assert "take_0001" in ask_data["supporting_take_ids"]
        assert any("take_0001" in claim["supporting_take_ids"] for claim in ask_data["claims"])

        briefing_payload = {"focus": "Project Harbor payment recovery workstream Priya Sharma", "project_id": "project-harbor"}
        res_briefing = client.post("/briefings", json=briefing_payload)
        assert res_briefing.status_code == 200
        briefing_data = res_briefing.json()
        assert briefing_data["status"] == "ANSWERED", f"Expected ANSWERED, got {briefing_data['status']}"
        assert "take_0001" in briefing_data["supporting_take_ids"]

        unrelated_payload = {"question": "Does it rain in space?", "project_id": "project-harbor"}
        res_unrelated = client.post("/ask", json=unrelated_payload)
        assert res_unrelated.status_code == 200
        assert res_unrelated.json()["status"] == "NO_EVIDENCE"

    finally:
        get_settings.cache_clear()
