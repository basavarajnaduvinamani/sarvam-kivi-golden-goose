from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
EVALUATION_DIR = ROOT / "evaluation"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_cases() -> list[dict[str, Any]]:
    projects = json.loads((CORPUS_DIR / "projects.json").read_text(encoding="utf-8"))
    records = {item["take_id"]: item for item in _load_jsonl(CORPUS_DIR / "kivi_500.jsonl")}
    labels = _load_jsonl(CORPUS_DIR / "gold_labels.jsonl")
    by_project: dict[str, dict[str, dict[str, Any]]] = {}
    for label in labels:
        if label["project_id"]:
            by_project.setdefault(label["project_id"], {})[label["scenario_type"]] = label

    cases: list[dict[str, Any]] = []

    def add(
        category: str,
        project_id: str | None,
        question: str,
        expected_status: str,
        *,
        description: str,
        contains: list[str] | None = None,
        excludes: list[str] | None = None,
        take_ids: list[str] | None = None,
        action: str = "ask",
        action_take_id: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        cases.append(
            {
                "case_id": f"eval_{len(cases) + 1:03d}",
                "category": category,
                "description": description,
                "project_id": project_id,
                "question": question,
                "setup": {"action": action, "take_id": action_take_id},
                "expected": {
                    "status": expected_status,
                    "contains": contains or [],
                    "excludes": excludes or [],
                    "supporting_take_ids": take_ids or [],
                },
                "metric_tags": tags or [category],
            }
        )

    # 1. Explicit entity and selected-project disagreement must never leak (12).
    for index in range(12):
        selected = projects[index]
        referenced = projects[(index + 1) % len(projects)]
        add(
            "project_isolation",
            selected["id"],
            f"What is {referenced['name']}'s current review schedule?",
            "NEEDS_CLARIFICATION",
            description="A selected project conflicts with a different explicit project in the question.",
            excludes=[referenced["name"]],
            tags=["project_scope", "cross_project_leakage"],
        )

    # 2. Facts captured across applications remain recoverable inside one project (12).
    for project in projects[:12]:
        label = by_project[project["id"]]["cross_application_fact"]
        memory = label["expected_memories"][0]
        add(
            "cross_application_recovery",
            project["id"],
            f"For {project['name']}, what is the working draft location?",
            "ANSWERED",
            description="Recover a project fact regardless of its source application.",
            contains=[memory["object_value"]],
            take_ids=[label["take_id"]],
            tags=["answer_correctness", "cross_application", "provenance"],
        )

    # 3. One answer may require two independently captured takes (12).
    for project in projects[:12]:
        owner = by_project[project["id"]]["distributed_owner"]
        reviewer = by_project[project["id"]]["distributed_reviewer"]
        add(
            "distributed_evidence",
            project["id"],
            f"For {project['name']}, who is the login demonstration owner and who is the payment recovery reviewer?",
            "ANSWERED",
            description="A complete answer requires two separately captured ownership facts.",
            contains=[owner["expected_memories"][0]["object_value"], reviewer["expected_memories"][0]["object_value"]],
            take_ids=[owner["take_id"], reviewer["take_id"]],
            tags=["answer_correctness", "distributed_evidence", "provenance"],
        )

    # 4. Corrections replace current state without erasing history (12).
    for project in projects[:12]:
        old = by_project[project["id"]]["initial_schedule"]
        current = by_project[project["id"]]["schedule_correction"]
        add(
            "temporal_correction",
            project["id"],
            f"What is the latest approved review schedule for {project['name']}?",
            "ANSWERED",
            description="Return the corrected schedule and exclude the superseded value.",
            contains=[current["expected_memories"][0]["object_value"]],
            excludes=[old["expected_memories"][0]["object_value"]],
            take_ids=[current["take_id"]],
            tags=["answer_correctness", "temporal_correction", "provenance"],
        )

    # 5. Non-approved language retains its epistemic force (12).
    epistemic_scenarios = ["rejected_proposal", "conditional_action", "quoted_hypothetical", "negative_state", "counterfactual"]
    for index, project in enumerate(projects[:12]):
        scenario = epistemic_scenarios[index % len(epistemic_scenarios)]
        label = by_project[project["id"]][scenario]
        memory = label["expected_memories"][0]
        required_word = "rejected" if memory["epistemic_status"] == "REJECTED" else "conditional" if memory["epistemic_status"] == "CONDITIONAL" else memory["object_value"]
        add(
            "epistemic_safety",
            project["id"],
            f"For {project['name']}, what status applies to {memory['predicate']} described as {memory['object_value']}?",
            "ANSWERED",
            description="Preserve rejected, conditional, hypothetical, counterfactual, or negative status.",
            contains=[required_word],
            take_ids=[label["take_id"]],
            tags=["answer_correctness", "decision_status", "rejected_promotion", "provenance"],
        )

    # 6. Unsupported questions abstain and unscoped questions request clarification (12).
    for project in projects[:6]:
        add(
            "abstention_and_scope",
            project["id"],
            f"What catering menu was approved for {project['name']}?",
            "NO_EVIDENCE",
            description="No project evidence discusses catering.",
            tags=["abstention", "fabricated_answer"],
        )
    for project in projects[6:12]:
        add(
            "abstention_and_scope",
            None,
            f"What is the current status of {project['name']}?",
            "NEEDS_CLARIFICATION",
            description="No explicit project scope was supplied to the request contract.",
            tags=["abstention", "project_scope"],
        )

    # 7. Answers cite the exact technical/customer-constraint source (12).
    for index, project in enumerate(projects[:12]):
        scenario = "technical_identifier" if index % 2 == 0 else "customer_constraint"
        label = by_project[project["id"]][scenario]
        memory = label["expected_memories"][0]
        add(
            "provenance",
            project["id"],
            f"For {project['name']}, what is the {memory['predicate']}?",
            "ANSWERED",
            description="The answer must cite the exact take supporting the complete claim.",
            contains=[memory["object_value"]],
            take_ids=[label["take_id"]],
            tags=["answer_correctness", "provenance", "invalid_citation"],
        )

    # 8. Deleted sentinels stay unavailable; alternating cases rebuild the index (12).
    for index, project in enumerate(projects[:12]):
        label = by_project[project["id"]]["deletion_sentinel"]
        marker = label["expected_memories"][0]["object_value"]
        add(
            "deletion_integrity",
            project["id"],
            f"Is the temporary deletion marker {marker} still recorded for {project['name']}?",
            "NO_EVIDENCE",
            description="Delete the sentinel before asking and ensure no query path resurrects it.",
            excludes=[marker],
            action="delete_rebuild_ask" if index % 2 else "delete_restart_ask",
            action_take_id=label["take_id"],
            tags=["deletion_integrity", "deleted_resurrection", "fabricated_answer"],
        )

    # 9. Service failures differ from unresolved conflicts (6 + 6).
    for project in projects[:6]:
        add(
            "service_and_conflict",
            project["id"],
            f"What is the current review schedule for {project['name']}?",
            "SERVICE_ERROR",
            description="A provider outage must be typed as SERVICE_ERROR, not missing evidence.",
            action="service_error",
            tags=["service_failure"],
        )
    for project in projects[6:12]:
        current = by_project[project["id"]]["schedule_correction"]
        add(
            "service_and_conflict",
            project["id"],
            f"What is the approved review schedule for {project['name']}?",
            "CONFLICTING_EVIDENCE",
            description="Two active approved schedules must produce an explicit conflict.",
            take_ids=[current["take_id"]],
            action="inject_conflict",
            action_take_id=current["take_id"],
            tags=["conflict_detection", "provenance"],
        )

    # 10. Indic code-switching and protected identifiers remain recoverable (12).
    for index, project in enumerate(projects[:12]):
        scenario = "hindi_code_switch" if index % 2 == 0 else "kannada_code_switch"
        label = by_project[project["id"]][scenario]
        memory = label["expected_memories"][0]
        qualifier = memory["object_value"] if scenario == "kannada_code_switch" else "touch constraint"
        add(
            "multilingual_identifiers",
            project["id"],
            f"{project['name']} production database {qualifier} क्या है?",
            "ANSWERED",
            description="Recover an Indic code-switched constraint without losing protected terms.",
            contains=["production database", memory["object_value"]],
            take_ids=[label["take_id"]],
            tags=["answer_correctness", "multilingual", "provenance"],
        )

    # 11. General and application-specific preferences remain distinguishable (12).
    for index, project in enumerate(projects[:12]):
        scenario = "application_preference" if index % 2 == 0 else "durable_preference"
        label = by_project[project["id"]][scenario]
        memory = label["expected_memories"][0]
        question = (
            f"For {project['name']}, what writing format applies specifically in ChatGPT and Notepad?"
            if scenario == "application_preference"
            else f"For {project['name']} customer updates, what format does the owner prefer?"
        )
        add(
            "preference_precedence",
            project["id"],
            question,
            "ANSWERED",
            description="Retrieve the correctly scoped general or application-specific preference.",
            contains=[memory["object_value"]],
            take_ids=[label["take_id"]],
            tags=["answer_correctness", "preference", "provenance"],
        )

    if len(cases) != 132:
        raise AssertionError(f"expected exactly 132 cases, generated {len(cases)}")
    if len({case["case_id"] for case in cases}) != 132:
        raise AssertionError("evaluation case IDs must be unique")
    return cases


def render_jsonl(cases: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the deterministic 132-case Kivi evaluation")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render_jsonl(build_cases())
    target = EVALUATION_DIR / "cases.jsonl"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != expected:
            raise SystemExit("evaluation/cases.jsonl is stale or missing")
        print("Evaluation case verification passed: 132 deterministic cases.")
        return
    target.write_text(expected, encoding="utf-8", newline="\n")
    print("Generated 132 deterministic evaluation cases.")


if __name__ == "__main__":
    main()
