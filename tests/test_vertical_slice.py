from datetime import datetime, timezone
from hashlib import sha256


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
    expected_memory_id = f"mem_{sha256('take_0001|0|1.0'.encode()).hexdigest()[:32]}"
    assert payload["memories"][0]["id"] == expected_memory_id
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


def test_deleted_take_is_purged_and_cannot_support_future_answers(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": []},
    )
    text = "Project Harbor's confirmed release is Thursday at 4 PM."
    client.post(
        "/takes",
        json={
            "take_id": "take_delete_me",
            "project_id": "project-harbor",
            "raw_asr": text,
            "formatted_text": text,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {"temporary": True},
        },
    )

    deleted = client.delete("/takes/take_delete_me")
    assert deleted.status_code == 200, deleted.text
    deletion = deleted.json()
    assert deletion["logically_deleted"] is True
    assert deletion["tombstone"]["purge_status"] == "purged"
    assert deletion["tombstone"]["verified_at"] is not None
    assert len(deletion["invalidated_memory_ids"]) == 1

    status = client.get("/deletions/take_delete_me")
    assert status.status_code == 200
    assert status.json()["purge_status"] == "purged"

    answer = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    )
    assert answer.status_code == 200
    assert answer.json()["status"] == "NO_EVIDENCE"
    assert answer.json()["supporting_take_ids"] == []


def test_unscoped_take_is_preserved_without_creating_memory(client):
    text = "A note without an explicitly confirmed project."
    response = client.post(
        "/takes",
        json={
            "take_id": "take_unscoped",
            "raw_asr": text,
            "formatted_text": text,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["take"]["project_id"] is None
    assert payload["memories"] == []
    assert "scope is unresolved" in payload["ignored_reason"]


def test_explicit_correction_supersedes_matching_active_memory(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": []},
    )
    first_text = "Project Harbor's release is approved for Tuesday at 9 AM."
    first = client.post(
        "/takes",
        json={
            "take_id": "take_old",
            "project_id": "project-harbor",
            "raw_asr": first_text,
            "formatted_text": first_text,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {"object_value": "Tuesday at 9 AM"},
        },
    )
    old_memory_id = first.json()["memories"][0]["id"]
    correction_text = "Correction: Project Harbor's release is approved for Thursday at 4 PM."
    corrected = client.post(
        "/takes",
        json={
            "take_id": "take_correction",
            "project_id": "project-harbor",
            "raw_asr": correction_text,
            "formatted_text": correction_text,
            "source_application": "ChatGPT",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "object_value": "Thursday at 4 PM",
                "supersedes_memory_id": old_memory_id,
            },
        },
    )
    assert corrected.status_code == 201, corrected.text
    assert corrected.json()["memories"][0]["supersedes_memory_id"] == old_memory_id

    answer = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    ).json()
    assert answer["status"] == "ANSWERED"
    assert "Thursday at 4 PM" in answer["answer"]
    assert answer["supporting_take_ids"] == ["take_correction"]


def test_correction_type_links_exactly_one_matching_active_memory(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": []},
    )
    initial_text = "Project Harbor's release is approved for Tuesday at 9 AM."
    initial = client.post(
        "/takes",
        json={
            "take_id": "take_auto_old",
            "project_id": "project-harbor",
            "raw_asr": initial_text,
            "formatted_text": initial_text,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {"object_value": "Tuesday at 9 AM"},
        },
    ).json()
    old_memory_id = initial["memories"][0]["id"]
    correction_text = "Correction: Project Harbor's release is Thursday at 4 PM."
    correction = client.post(
        "/takes",
        json={
            "take_id": "take_auto_new",
            "project_id": "project-harbor",
            "raw_asr": correction_text,
            "formatted_text": correction_text,
            "source_application": "ChatGPT",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {"object_value": "Thursday at 4 PM", "memory_type": "correction"},
        },
    )
    assert correction.status_code == 201, correction.text
    assert correction.json()["memories"][0]["supersedes_memory_id"] == old_memory_id


def test_unresolved_approved_values_return_conflict(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": []},
    )
    for take_id, value in (("take_tuesday", "Tuesday at 9 AM"), ("take_friday", "Friday at 2 PM")):
        text = f"Project Harbor's release is approved for {value}."
        response = client.post(
            "/takes",
            json={
                "take_id": take_id,
                "project_id": "project-harbor",
                "raw_asr": text,
                "formatted_text": text,
                "source_application": "Notepad",
                "event_ts": datetime.now(timezone.utc).isoformat(),
                "metadata": {"object_value": value},
            },
        )
        assert response.status_code == 201

    answer = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    ).json()
    assert answer["status"] == "CONFLICTING_EVIDENCE"
    assert set(answer["supporting_take_ids"]) == {"take_tuesday", "take_friday"}
    assert len(answer["claims"]) == 2


def test_active_approved_memories_with_different_person_names_produce_conflict(client):
    from kivi.services.retrieval import _semantically_equivalent_values

    assert not _semantically_equivalent_values(["Maya Rao", "Priya Sharma"])
    assert not _semantically_equivalent_values(["wait for Maya Rao approval", "wait for Priya Sharma approval"])

    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": ["Harbor"]},
    )
    for take_id, person_name in (("take_maya", "Maya Rao"), ("take_priya", "Priya Sharma")):
        text = f"Project Harbor's release lead is {person_name}."
        response = client.post(
            "/takes",
            json={
                "take_id": take_id,
                "project_id": "project-harbor",
                "raw_asr": text.lower(),
                "formatted_text": text,
                "source_application": "Notepad",
                "event_ts": datetime.now(timezone.utc).isoformat(),
                "metadata": {"object_value": person_name},
            },
        )
        assert response.status_code == 201

    answer = client.post(
        "/ask",
        json={"project_id": "project-harbor", "question": "When is the Harbor release?"},
    ).json()
    assert answer["status"] == "CONFLICTING_EVIDENCE"
    assert set(answer["supporting_take_ids"]) == {"take_maya", "take_priya"}
    assert len(answer["claims"]) == 2


def test_bulk_import_reports_scoped_unscoped_and_failed_records(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": []},
    )
    now = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "take_id": "bulk_scoped",
            "project_id": "project-harbor",
            "raw_asr": "harbor release thursday",
            "formatted_text": "Project Harbor's release is Thursday at 4 PM.",
            "source_application": "Notepad",
            "event_ts": now,
            "metadata": {},
        },
        {
            "take_id": "bulk_unscoped",
            "raw_asr": "miscellaneous note",
            "formatted_text": "A miscellaneous note without project scope.",
            "source_application": "Slack",
            "event_ts": now,
            "metadata": {},
        },
        {
            "take_id": "bulk_missing_project",
            "project_id": "missing",
            "raw_asr": "unknown project",
            "formatted_text": "Unknown project note.",
            "source_application": "Terminal",
            "event_ts": now,
            "metadata": {},
        },
    ]
    response = client.post("/takes/import", json=records)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["total"] == 3
    assert result["ingested"] == 2
    assert result["memories_created"] == 1
    assert result["unscoped"] == 1
    assert result["failed"] == 1
    assert result["errors"][0]["take_id"] == "bulk_missing_project"


def test_inspection_endpoints_expose_source_and_lifecycle_state(client):
    client.post(
        "/projects",
        json={"id": "project-harbor", "name": "Project Harbor", "aliases": ["Harbor"]},
    )
    text = "Project Harbor's release is Thursday at 4 PM."
    ingested = client.post(
        "/takes",
        json={
            "take_id": "take_inspect",
            "project_id": "project-harbor",
            "raw_asr": text.lower(),
            "formatted_text": text,
            "source_application": "Notepad",
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        },
    ).json()
    memory_id = ingested["memories"][0]["id"]

    assert client.get("/projects").json()[0]["id"] == "project-harbor"
    assert client.get("/takes", params={"project_id": "project-harbor"}).json()[0]["id"] == "take_inspect"
    assert client.get("/takes/take_inspect").json()["formatted_text"] == text
    memory = client.get(f"/memories/{memory_id}").json()
    assert memory["lifecycle_status"] == "ACTIVE"
    assert memory["evidence"][0]["take_id"] == "take_inspect"
    active = client.get(
        "/memories",
        params={"project_id": "project-harbor", "lifecycle_status": "ACTIVE"},
    ).json()
    assert [item["id"] for item in active] == [memory_id]

