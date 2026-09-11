from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..db import build_engine
from ..enums import LifecycleStatus, QueryStatus
from ..models import Memory, Project, QueryRun
from ..providers import GroundedAnswerer, MemoryExtractor
from ..schemas import (
    AskRequest, EvaluationCaseResultRead, EvaluationCategoryMetrics, EvaluationMetricsRead,
    EvaluationRunRead, TakeCreate,
)
from ..services.corpus_import import import_takes
from ..services.deletion import delete_take
from ..services.indexing import rebuild_memory_fts
from ..services.retrieval import ask
from .providers import DeterministicAnswerer, DeterministicEmbedder, FailingEmbedder, GoldExtractor


ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = ROOT / "evaluation"
RESULTS_DIR = ROOT / "results"
VAR_DIR = ROOT / "var"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _migrate(database_path: Path) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")


def _database_bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return float(ordered[position])


def _inject_conflict(session: Session, correction_take_id: str) -> None:
    correction = session.scalar(select(Memory).where(Memory.id.like("mem_%"), Memory.evidence_links.any(take_id=correction_take_id)))
    if correction is None or correction.supersedes_memory_id is None:
        raise RuntimeError(f"cannot construct conflict for {correction_take_id}")
    old = session.get(Memory, correction.supersedes_memory_id)
    if old is None:
        raise RuntimeError("superseded memory is unavailable")
    old.lifecycle_status = LifecycleStatus.ACTIVE
    old.epistemic_status = "APPROVED"
    session.commit()


def _restore_conflict(session: Session, correction_take_id: str) -> None:
    correction = session.scalar(select(Memory).where(Memory.evidence_links.any(take_id=correction_take_id)))
    if correction and correction.supersedes_memory_id:
        old = session.get(Memory, correction.supersedes_memory_id)
        if old:
            old.lifecycle_status = LifecycleStatus.SUPERSEDED
            old.epistemic_status = "PROPOSED"
            session.commit()


def _evaluate_case(session_factory, case: dict, embedder, answerer) -> EvaluationCaseResultRead:
    started = perf_counter()
    action = case["setup"]["action"]
    take_id = case["setup"]["take_id"]
    with session_factory() as session:
        if action.startswith("delete_"):
            delete_take(session, take_id)
            if action == "delete_rebuild_ask":
                rebuild_memory_fts(session)
        elif action == "inject_conflict":
            _inject_conflict(session, take_id)

    # Reopening the session proves that committed lifecycle state, rather than
    # identity-map state from the mutation transaction, governs the query.
    with session_factory() as session:
        chosen_embedder = FailingEmbedder() if action == "service_error" else embedder
        response = ask(
            session,
            AskRequest(project_id=case["project_id"], question=case["question"]),
            chosen_embedder,
            answerer,
            similarity_threshold=0.45,
        )
        run = session.get(QueryRun, response.query_id)
        relevant_memory_ids = list(run.selected_memory_ids if run else [])

    if action == "inject_conflict":
        with session_factory() as session:
            _restore_conflict(session, take_id)

    expected = case["expected"]
    answer_text = response.answer or ""
    folded = answer_text.casefold()
    reasons: list[str] = []
    if response.status.value != expected["status"]:
        reasons.append(f"expected status {expected['status']}, received {response.status.value}")
    for value in expected["contains"]:
        if value.casefold() not in folded:
            reasons.append(f"answer omitted required text: {value}")
    for value in expected["excludes"]:
        if value.casefold() in folded:
            reasons.append(f"answer included prohibited text: {value}")
    if not set(expected["supporting_take_ids"]) <= set(response.supporting_take_ids):
        reasons.append("response omitted an expected supporting Take ID")
    actual = response.model_dump(mode="json")
    return EvaluationCaseResultRead(
        case_id=case["case_id"], category=case["category"], description=case["description"],
        project_id=case["project_id"], question=case["question"], expected_status=expected["status"],
        actual_status=response.status, passed=not reasons, failure_reasons=reasons, expected=expected, actual=actual,
        relevant_memory_ids=relevant_memory_ids, supporting_take_ids=response.supporting_take_ids,
        duration_ms=int((perf_counter() - started) * 1000), input_tokens=response.input_tokens,
        output_tokens=response.output_tokens, estimated_cost_usd=response.estimated_cost_usd,
    )


def _tagged(raw_cases: list[dict], results: list[EvaluationCaseResultRead], tag: str) -> list[EvaluationCaseResultRead]:
    ids = {case["case_id"] for case in raw_cases if tag in case["metric_tags"]}
    return [case for case in results if case.case_id in ids]


def _tag_ratio(raw_cases: list[dict], results: list[EvaluationCaseResultRead], tag: str) -> float:
    selected = _tagged(raw_cases, results, tag)
    return sum(case.passed for case in selected) / len(selected) if selected else 1.0


def _metrics(raw_cases: list[dict], cases: list[EvaluationCaseResultRead], before: int, after: int) -> EvaluationMetricsRead:
    by_category: dict[str, EvaluationCategoryMetrics] = {}
    for category in sorted({case.category for case in cases}):
        group = [case for case in cases if case.category == category]
        passed = sum(case.passed for case in group)
        by_category[category] = EvaluationCategoryMetrics(total=len(group), passed=passed, failed=len(group)-passed, pass_rate=passed/len(group))
    passed = sum(case.passed for case in cases)
    abstain_expected = {QueryStatus.NO_EVIDENCE, QueryStatus.NEEDS_CLARIFICATION}
    predicted = [case for case in cases if case.actual_status in abstain_expected]
    expected = [case for case in cases if case.expected_status in abstain_expected]
    true_positive = sum(case.actual_status in abstain_expected and case.expected_status in abstain_expected for case in cases)
    retrieval = [int(case.actual.get("retrieval_latency_ms", 0)) for case in cases]
    end_to_end = [int(case.actual.get("end_to_end_latency_ms", 0)) for case in cases]
    def violations(tag: str) -> int:
        return sum(not case.passed for case in _tagged(raw_cases, cases, tag))
    costs = [case.estimated_cost_usd for case in cases if case.estimated_cost_usd is not None]
    return EvaluationMetricsRead(
        total_cases=len(cases), passed=passed, failed=len(cases)-passed, pass_rate=passed/len(cases),
        answer_correctness=_tag_ratio(raw_cases, cases, "answer_correctness"),
        abstention_precision=true_positive/len(predicted) if predicted else 1.0,
        abstention_recall=true_positive/len(expected) if expected else 1.0,
        conflict_detection_accuracy=_tag_ratio(raw_cases, cases, "conflict_detection"),
        project_scope_accuracy=_tag_ratio(raw_cases, cases, "project_scope"),
        decision_status_accuracy=_tag_ratio(raw_cases, cases, "decision_status"),
        temporal_correction_accuracy=_tag_ratio(raw_cases, cases, "temporal_correction"),
        provenance_coverage=_tag_ratio(raw_cases, cases, "provenance"),
        deletion_integrity=_tag_ratio(raw_cases, cases, "deletion_integrity"),
        cross_project_leakage_count=violations("cross_project_leakage"),
        deleted_memory_resurrection_count=violations("deleted_resurrection"),
        invalid_citation_count=violations("invalid_citation"),
        rejected_proposal_promotion_count=violations("rejected_promotion"),
        fabricated_answer_count=violations("fabricated_answer"),
        retrieval_latency_p50_ms=_percentile(retrieval, .50), retrieval_latency_p95_ms=_percentile(retrieval, .95),
        end_to_end_latency_p50_ms=_percentile(end_to_end, .50), end_to_end_latency_p95_ms=_percentile(end_to_end, .95),
        database_bytes_before=before, database_bytes_after=after, database_growth_bytes=after-before,
        input_tokens=sum(case.input_tokens or 0 for case in cases), output_tokens=sum(case.output_tokens or 0 for case in cases),
        estimated_cost_usd=sum(costs) if costs else None, by_category=by_category,
    )


def _write_results(run: EvaluationRunRead) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = run.model_dump_json(indent=2)
    (RESULTS_DIR / "latest.json").write_text(payload + "\n", encoding="utf-8", newline="\n")
    lines = ["# Kivi Evaluation Results", "", f"Run: `{run.run_id}`", f"Mode: `{run.mode}`", "", "## Summary", "",
             f"- Cases: {run.case_count}", f"- Passed: {run.metrics.passed}", f"- Failed: {run.metrics.failed}",
             f"- Pass rate: {run.metrics.pass_rate:.1%}", "", "## Categories", "", "| Category | Passed | Total | Rate |", "|---|---:|---:|---:|"]
    for name, metric in run.metrics.by_category.items():
        lines.append(f"| {name} | {metric.passed} | {metric.total} | {metric.pass_rate:.1%} |")
    failures = [case for case in run.cases if not case.passed]
    lines.extend(["", "## Failures", ""])
    lines.extend([f"- `{case.case_id}`: {'; '.join(case.failure_reasons)}" for case in failures] or ["No failures."])
    (RESULTS_DIR / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_evaluation(mode: str = "deterministic") -> EvaluationRunRead:
    if mode not in {"deterministic", "candidate"}:
        raise ValueError("mode must be deterministic or candidate")
    started = datetime.now(timezone.utc)
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    database_path = VAR_DIR / "evaluation.db"
    if database_path.exists():
        database_path.unlink()
    _migrate(database_path)
    before = _database_bytes(database_path)
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    projects = json.loads((ROOT / "corpus" / "projects.json").read_text(encoding="utf-8"))
    records = [TakeCreate.model_validate(item) for item in _jsonl(ROOT / "corpus" / "kivi_500.jsonl")]
    if mode == "deterministic":
        extractor: MemoryExtractor = GoldExtractor()
        embedder = DeterministicEmbedder()
        answerer: GroundedAnswerer = DeterministicAnswerer()
    else:
        from ..app import default_provider_bundle

        bundle = default_provider_bundle()
        extractor, embedder, answerer = bundle.extractor, bundle.embedder, bundle.answerer
    with factory() as session:
        session.add_all([Project(id=item["id"], name=item["name"], aliases=item["aliases"]) for item in projects])
        session.commit()
        imported = import_takes(session, records, extractor, embedder)
        if imported.ingested != 500 or imported.failed:
            raise RuntimeError(f"evaluation corpus import failed: {imported.model_dump()}")
        rebuild_memory_fts(session)
    raw_cases = _jsonl(EVALUATION_DIR / "cases.jsonl")
    results = [_evaluate_case(factory, case, embedder, answerer) for case in raw_cases]
    after = _database_bytes(database_path)
    run = EvaluationRunRead(
        run_id=f"evalrun_{uuid4().hex[:12]}", mode=mode, started_at=started, completed_at=datetime.now(timezone.utc),
        corpus_record_count=500, case_count=len(results), metrics=_metrics(raw_cases, results, before, after), cases=results,
        results_json_path="results/latest.json", report_markdown_path="results/latest.md",
    )
    _write_results(run)
    return run


def get_latest_run() -> EvaluationRunRead:
    path = RESULTS_DIR / "latest.json"
    if not path.exists():
        raise FileNotFoundError("no evaluation run is available")
    return EvaluationRunRead.model_validate_json(path.read_text(encoding="utf-8"))


def get_case_result(case_id: str) -> EvaluationCaseResultRead:
    run = get_latest_run()
    for case in run.cases:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
