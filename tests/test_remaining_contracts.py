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


def test_user_correction_creates_evidence_and_supersedes_original(client):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor", "aliases": []})
    original = _ingest(client, "take_original", "Tuesday at 9 AM").json()
    original_memory_id = original["memories"][0]["id"]

    response = client.post(
        f"/memories/{original_memory_id}/correct",
        json={"corrected_value": "Thursday at 4 PM", "note": "Confirmed by Maya"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    correction = payload["memories"][0]
    assert correction["memory_type"] == "correction"
    assert correction["epistemic_status"] == "APPROVED"
    assert correction["lifecycle_status"] == "ACTIVE"
    assert correction["supersedes_memory_id"] == original_memory_id
    assert correction["object_value"] == "Thursday at 4 PM"
    assert correction["extraction_method"] == "user_confirmed_correction"
    assert correction["evidence"][0]["take_id"] == payload["take"]["id"]
    assert payload["take"]["source_application"] == "Kivi Memory Inspector"

    timeline = client.get("/projects/project-harbor/timeline").json()
    entries = {entry["memory_id"]: entry for entry in timeline["entries"]}
    assert entries[original_memory_id]["lifecycle_status"] == "SUPERSEDED"
    assert entries[original_memory_id]["valid_to"] is not None
    assert entries[correction["id"]]["lifecycle_status"] == "ACTIVE"

    answer = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    ).json()
    assert answer["status"] == "ANSWERED"
    assert "Thursday at 4 PM" in answer["answer"]
    assert answer["supporting_take_ids"] == [payload["take"]["id"]]


def test_unscoped_take_can_be_explicitly_assigned_and_processed(client):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor", "aliases": []})
    created = client.post(
        "/takes",
        json={
            "take_id": "take_unscoped_assignment",
            "raw_asr": "harbor release thursday",
            "formatted_text": "Project Harbor's release is Thursday at 4 PM.",
            "source_application": "Notepad",
            "event_ts": "2026-09-11T09:00:00Z",
            "metadata": {"object_value": "Thursday at 4 PM"},
        },
    )
    assert created.status_code == 201
    assert created.json()["memories"] == []
    assert [item["id"] for item in client.get("/takes", params={"unscoped_only": True}).json()] == [
        "take_unscoped_assignment"
    ]

    assigned = client.post(
        "/takes/take_unscoped_assignment/scope",
        json={"project_id": "project-harbor"},
    )
    assert assigned.status_code == 200, assigned.text
    payload = assigned.json()
    assert payload["take"]["project_id"] == "project-harbor"
    assert payload["memories"][0]["evidence"][0]["take_id"] == "take_unscoped_assignment"
    assert client.get("/takes", params={"unscoped_only": True}).json() == []


def test_scope_assignment_rejects_reassignment(client):
    client.post("/projects", json={"id": "project-harbor", "name": "Project Harbor", "aliases": []})
    _ingest(client, "take_scoped", "Thursday at 4 PM")
    response = client.post("/takes/take_scoped/scope", json={"project_id": "project-harbor"})
    assert response.status_code == 409
    assert "already has confirmed project scope" in response.json()["detail"]
