from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from kivi.schemas import EvaluationRunRequest


def _ingest(client, take_id: str, value: str, *, memory_type: str = "decision", supersedes: str | None = None):
    content = f"Project Harbor's release schedule is {value}."
    metadata = {"object_value": value, "memory_type": memory_type}
    if supersedes:
        metadata["supersedes_memory_id"] = supersedes
    return client.post(
        "/takes",
        json={
            "take_id": take_id,
            "project_id": "project-harbor",
            "raw_asr": content.lower(),
            "formatted_text": content,
            "source_application": "Notepad" if take_id.endswith("old") else "ChatGPT",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        },
    )


def test_timeline_exposes_epistemic_lifecycle_supersession_and_evidence(client):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor", "aliases": ["Harbor"]})
    old = _ingest(client, "take_old", "Tuesday at 9 AM").json()
    old_memory_id = old["memories"][0]["id"]
    new = _ingest(client, "take_new", "Thursday at 4 PM", memory_type="correction", supersedes=old_memory_id).json()
    new_memory_id = new["memories"][0]["id"]

    response = client.get("/projects/project-harbor/timeline")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == "project-harbor"
    entries = {entry["memory_id"]: entry for entry in payload["entries"]}
    assert entries[old_memory_id]["epistemic_status"] == "APPROVED"
    assert entries[old_memory_id]["lifecycle_status"] == "SUPERSEDED"
    assert entries[old_memory_id]["superseded_by_memory_ids"] == [new_memory_id]
    assert entries[new_memory_id]["supersedes_memory_id"] == old_memory_id
    assert entries[new_memory_id]["evidence"][0]["take_id"] == "take_new"
    assert entries[new_memory_id]["evidence"][0]["source_application"] == "ChatGPT"
    assert entries[new_memory_id]["evidence"][0]["is_required"] is True


def test_unknown_timeline_is_404(client):
    response = client.get("/projects/missing/timeline")
    assert response.status_code == 404
    assert "unknown project_id" in response.json()["detail"]


def test_briefing_reuses_grounded_claim_citation_contract(client):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor", "aliases": []})
    _ingest(client, "take_brief", "Thursday at 4 PM")
    response = client.post(
        "/briefings",
        json={"project_id": "project-harbor", "focus": "When is the Harbor release?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ANSWERED"
    assert payload["claims"][0]["supporting_take_ids"] == ["take_brief"]


def test_evaluation_mode_contract_rejects_unknown_modes():
    assert EvaluationRunRequest(mode="deterministic").mode == "deterministic"
    assert EvaluationRunRequest(mode="candidate").mode == "candidate"
    with pytest.raises(ValidationError):
        EvaluationRunRequest(mode="unknown")
