from datetime import datetime, timezone


def test_take_to_memory_to_grounded_answer(client):
    project = client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": ["Harbor"]},
    )
    assert project.status_code == 201

    text = "Correction for Project Harbor: the release moved to Thursday at 4 PM."
    ingested = client.post(
        "/takes",
        json={
            "take_id": "take_0001",
            "project_id": "project-harbor",
            "raw_asr": text.lower(),
            "formatted_text": text,
            "source_application": "ChatGPT",
            "event_ts": datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc).isoformat(),
            "metadata": {},
        },
    )
    assert ingested.status_code == 201, ingested.text
    payload = ingested.json()
    assert payload["take"]["id"] == "take_0001"
    assert len(payload["memories"]) == 1
    assert payload["memories"][0]["evidence"][0]["take_id"] == "take_0001"

    response = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    )
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["status"] == "ANSWERED"
    assert answer["supporting_take_ids"] == ["take_0001"]
    assert answer["claims"][0]["supporting_take_ids"] == ["take_0001"]
    assert "Thursday at 4 PM" in answer["answer"]


def test_missing_project_scope_abstains_before_embedding(client):
    response = client.post("/ask", json={"question": "When is the release?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NEEDS_CLARIFICATION"
    assert payload["answer"] is None
    assert payload["supporting_take_ids"] == []


def test_unknown_project_cannot_ingest_memory(client):
    response = client.post(
        "/takes",
        json={
            "take_id": "take_orphan",
            "project_id": "missing",
            "raw_asr": "orphan",
            "formatted_text": "Orphan.",
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        },
    )
    assert response.status_code == 422
    assert "unknown project_id" in response.json()["detail"]

