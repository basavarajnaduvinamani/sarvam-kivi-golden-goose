from __future__ import annotations

import json

import pytest

from kivi.cli import build_parser, load_corpus


def test_reviewer_cli_exposes_required_operations():
    parser = build_parser()
    assert parser.parse_args(["serve"]).command == "serve"
    assert parser.parse_args(["db", "migrate"]).db_command == "migrate"
    assert parser.parse_args(["db", "rebuild-index"]).db_command == "rebuild-index"
    assert parser.parse_args(["projects", "import", "projects.json"]).project_command == "import"
    assert parser.parse_args(["corpus", "validate", "corpus.jsonl"]).expected_count == 500
    assert parser.parse_args(["inspect", "--project-id", "project-harbor"]).project_id == "project-harbor"


def test_corpus_validation_rejects_count_mismatch_and_duplicate_ids(tmp_path):
    record = {"take_id": "take_1", "project_id": None, "raw_asr": "test", "formatted_text": "Test.", "source_application": "Notepad", "event_ts": "2026-09-10T00:00:00Z", "metadata": {}}
    path = tmp_path / "duplicate.jsonl"
    path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="duplicate take IDs"):
        load_corpus(path, 2)
    with pytest.raises(SystemExit, match="expected 500 records, found 2"):
        load_corpus(path, 500)


def test_cli_serve_resolves_app_without_pythonpath(monkeypatch):
    import sys
    from fastapi import FastAPI
    import uvicorn
    from kivi.cli import main

    captured = {}

    def fake_run(app, host, port):
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(uvicorn, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["kivi", "serve", "--port", "8005"])
    monkeypatch.delenv("PYTHONPATH", raising=False)

    main()

    assert isinstance(captured["app"], FastAPI)
    assert not isinstance(captured["app"], str)
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8005
