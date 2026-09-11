from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import kivi.evaluation as evaluation_package
from kivi.app import create_app
from kivi.cli import build_parser
from kivi.evaluation import runner


ROOT = Path(__file__).resolve().parents[1]


def test_committed_evaluation_is_exactly_132_deterministic_cases():
    cases = [
        json.loads(line)
        for line in (ROOT / "evaluation" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(cases) == 132
    assert len({case["case_id"] for case in cases}) == 132
    categories = {case["category"] for case in cases}
    assert len(categories) == 11
    assert all(sum(case["category"] == category for case in cases) == 12 for category in categories)
    assert {case["expected"]["status"] for case in cases} == {
        "ANSWERED", "NO_EVIDENCE", "NEEDS_CLARIFICATION", "CONFLICTING_EVIDENCE", "SERVICE_ERROR"
    }


def test_evaluation_generator_matches_committed_file():
    from evaluation.generate_cases import build_cases, render_jsonl

    assert (ROOT / "evaluation" / "cases.jsonl").read_text(encoding="utf-8") == render_jsonl(build_cases())


def test_deterministic_evaluation_runs_real_pipeline_and_writes_results(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "VAR_DIR", tmp_path / "var")
    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path / "results")
    run = runner.run_evaluation("deterministic")
    assert run.corpus_record_count == 500
    assert run.case_count == 132
    assert run.metrics.total_cases == 132
    assert run.metrics.passed == 132
    assert run.metrics.failed == 0
    assert run.metrics.cross_project_leakage_count == 0
    assert run.metrics.deleted_memory_resurrection_count == 0
    assert run.metrics.invalid_citation_count == 0
    assert run.metrics.rejected_proposal_promotion_count == 0
    assert run.metrics.fabricated_answer_count == 0
    assert len(run.metrics.by_category) == 11
    assert (tmp_path / "results" / "latest.json").exists()
    assert (tmp_path / "results" / "latest.md").exists()
    assert runner.get_latest_run().run_id == run.run_id
    assert runner.get_case_result("eval_001").case_id == "eval_001"

    monkeypatch.setattr(evaluation_package, "get_latest_run", lambda: run)
    monkeypatch.setattr(evaluation_package, "get_case_result", lambda case_id: run.cases[0])
    client = TestClient(create_app())
    assert client.get("/evaluate/latest").json()["case_count"] == 132
    assert client.get("/evaluate/cases/eval_001").json()["case_id"] == "eval_001"


def test_cli_exposes_both_evaluation_modes():
    parser = build_parser()
    assert parser.parse_args(["evaluate"]).mode == "deterministic"
    assert parser.parse_args(["evaluate", "--mode", "candidate"]).mode == "candidate"
