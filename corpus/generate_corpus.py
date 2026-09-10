from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kivi.schemas import TakeCreate


SEED = 20260910
GENERATION_VERSION = "1.0"
PROJECTS = [
    ("project-harbor", "Project Harbor", "Priya Sharma", "Maya Rao", "PAY-401"),
    ("project-willow", "Project Willow", "Aaditya Kshatriya", "Maya Rao", "AUTH-218"),
    ("project-lotus", "Project Lotus", "Priya Sharma", "Neha Iyer", "OPS-742"),
    ("project-cedar", "Project Cedar", "Maya Rao", "Aaditya Kshatriya", "PAY-864"),
    ("project-nimbus", "Project Nimbus", "Riya Sen", "Priya Sharma", "WEB-315"),
    ("project-aurora", "Project Aurora", "Priya Sharma", "Maya Rao", "DES-119"),
    ("project-monsoon", "Project Monsoon", "Maya Rao", "Riya Sen", "REL-552"),
    ("project-quartz", "Project Quartz", "Aaditya Kshatriya", "Priya Sharma", "DB-581"),
    ("project-falcon", "Project Falcon", "Riya Sen", "Maya Rao", "API-525"),
    ("project-zina", "Project Zina", "Neha Iyer", "Priya Sharma", "SEC-079"),
    ("project-panyan", "Project Panyan", "Priya Sharma", "Aaditya Kshatriya", "PAY-429"),
    ("project-marigold", "Project Marigold", "Maya Rao", "Priya Sharma", "REL-410"),
    ("project-orbit", "Project Orbit", "Riya Sen", "Neha Iyer", "OPS-426"),
    ("project-lantern", "Project Lantern", "Neha Iyer", "Maya Rao", "OPS-953"),
    ("project-sedar", "Project Sedar", "Aaditya Kshatriya", "Maya Rao", "PAY-742"),
    ("project-ember", "Project Ember", "Priya Sharma", "Riya Sen", "AUTH-401"),
    ("project-river", "Project River", "Maya Rao", "Neha Iyer", "DATA-330"),
    ("project-meadow", "Project Meadow", "Neha Iyer", "Aaditya Kshatriya", "UX-204"),
    ("project-summit", "Project Summit", "Riya Sen", "Priya Sharma", "API-503"),
    ("project-cobalt", "Project Cobalt", "Aaditya Kshatriya", "Neha Iyer", "REL-215"),
]
APPLICATIONS = ["Notepad", "ChatGPT", "Slack", "Terminal"]


@dataclass(frozen=True)
class Scenario:
    category: str
    text: str
    should_create_memory: bool
    memory_type: str | None = None
    epistemic_status: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object_value: str | None = None
    supersedes_slot: int | None = None
    deletion_sentinel: bool = False
    scoped: bool = True


def scenarios(project: tuple[str, str, str, str, str], project_index: int) -> list[Scenario]:
    _project_id, name, owner, reviewer, ticket = project
    initial_day = ["Tuesday", "Wednesday", "Monday"][project_index % 3]
    corrected_day = ["Thursday", "Friday", "Wednesday"][project_index % 3]
    initial_time = ["9 AM", "10:15 AM", "11 AM"][project_index % 3]
    corrected_time = ["4 PM", "2:30 PM", "5:25 PM"][project_index % 3]
    feature = ["payment recovery", "login flow", "release checklist", "customer demo"][project_index % 4]
    return [
        Scenario("project_overview", f"{name} covers the {feature} workstream, owned by {owner}.", True, "episode", "APPROVED", name, "workstream", feature),
        Scenario("initial_schedule", f"The proposed {name} review is {initial_day} at {initial_time}; it is not approved yet.", True, "decision", "PROPOSED", name, "review schedule", f"{initial_day} at {initial_time}"),
        Scenario("schedule_correction", f"Correction for {name}: the review moved to {corrected_day} at {corrected_time}. The {initial_day} slot is cancelled, and this is the latest approved plan.", True, "correction", "APPROVED", name, "review schedule", f"{corrected_day} at {corrected_time}", supersedes_slot=1),
        Scenario("approval_constraint", f"Do not deploy {name} before {reviewer} approves the {feature} checks.", True, "constraint", "APPROVED", name, "deployment constraint", f"wait for {reviewer} approval"),
        Scenario("rejected_proposal", f"During brainstorming, someone suggested, \"delete the production database for {name}.\" That proposal was rejected and must never be treated as an instruction.", True, "rejected_proposal", "REJECTED", name, "production database deletion", "rejected"),
        Scenario("conditional_action", f"If {reviewer} confirms the recovery flow for {name}, archive the test logs; otherwise leave them unchanged.", True, "condition", "CONDITIONAL", name, "test log archival", f"only after {reviewer} confirms"),
        Scenario("commitment", f"{owner} committed to present the {feature} update for {name} at the next review.", True, "commitment", "APPROVED", name, "presentation owner", owner),
        Scenario("unresolved_question", f"It remains unresolved whether {name} should use a 15-minute or 20-minute session timeout.", True, "unresolved_question", "UNRESOLVED", name, "session timeout", "15 or 20 minutes"),
        Scenario("cross_application_fact", f"The latest {name} working draft is stored in the shared review folder and is still internal.", True, "episode", "APPROVED", name, "working draft location", "shared review folder"),
        Scenario("durable_preference", f"For {name} customer updates, {owner} prefers exactly three bullets with the decision first.", True, "preference", "APPROVED", owner, f"{name} update format", "three bullets, decision first"),
        Scenario("quoted_hypothetical", f"The sentence \"ship {name} without approval\" appeared only as a hypothetical example and is not an active instruction.", True, "rejected_proposal", "REJECTED", name, "unapproved shipment", "hypothetical only"),
        Scenario("negative_state", f"Deployment for {name} is not approved. Wait for {reviewer}'s confirmation.", True, "constraint", "APPROVED", name, "deployment status", "not approved"),
        Scenario("distributed_owner", f"For {name}, {owner} owns the login demonstration.", True, "commitment", "APPROVED", name, "login demonstration owner", owner),
        Scenario("distributed_reviewer", f"For {name}, {reviewer} owns payment recovery validation.", True, "commitment", "APPROVED", name, "payment recovery reviewer", reviewer),
        Scenario("semantic_leakage_trap", f"The {name} synchronization meeting will cover readiness, but it is not the customer demonstration.", True, "episode", "APPROVED", name, "synchronization meeting purpose", "readiness review"),
        Scenario("background_noise", "Background audio mentioned an unrelated football score and a restaurant booking; neither belongs to a work project.", False, scoped=False),
        Scenario("hindi_code_switch", f"{name} का customer demo कल 3:30 PM पर है। {owner} login flow दिखाएंगे और approval आने तक production database को touch मत करना।", True, "constraint", "APPROVED", name, "production database constraint", "do not touch until approval"),
        Scenario("kannada_code_switch", f"{name} customer demo ನಾಳೆ ಮಧ್ಯಾಹ್ನ 3:30ಕ್ಕೆ ಇದೆ. {reviewer} final approval ಕೊಡುವವರೆಗೆ production database ಅನ್ನು touch ಮಾಡಬೇಡಿ.", True, "constraint", "APPROVED", name, "production database constraint", f"do not touch until {reviewer} approves"),
        Scenario("approval_correction", f"Update for {name}: {reviewer} has not approved launch readiness. The earlier assumption of approval is withdrawn.", True, "correction", "APPROVED", name, "launch readiness", "not approved"),
        Scenario("customer_constraint", f"Customer data for {name} must not be copied into staging.", True, "constraint", "APPROVED", name, "customer data staging", "must not be copied"),
        Scenario("technical_identifier", f"The internal retry issue for {name} is tracked under {ticket}; the identifier must not appear in the customer brief.", True, "constraint", "APPROVED", name, "internal ticket", ticket),
        Scenario("application_preference", f"When drafting {name} updates in ChatGPT, use a structured goal-changes-validation format; keep Notepad output in complete sentences.", True, "preference", "APPROVED", owner, f"{name} application writing style", "ChatGPT structured; Notepad complete sentences"),
        Scenario("counterfactual", f"If {name} had missed the review, the demo would have moved by one week; this counterfactual did not happen.", True, "rejected_proposal", "REJECTED", name, "one-week demo delay", "counterfactual only"),
        Scenario("deletion_sentinel", f"Temporary deletion test for {name}. Access marker {ticket}-DELETE exists only for deletion verification and must be revoked.", True, "episode", "APPROVED", name, "temporary deletion marker", f"{ticket}-DELETE", deletion_sentinel=True),
        Scenario("current_summary", f"Current {name} summary: the {feature} remains in review, deployment is not approved, and {reviewer} is the approval owner.", True, "episode", "APPROVED", name, "current summary", f"{feature} in review; deployment not approved; approver {reviewer}"),
    ]


def raw_asr(text: str, rng: random.Random) -> str:
    replacements = {
        "Kivi": "kiwi",
        "Aaditya": "aditya",
        "3:30 PM": "three thirty pm",
        "10:15 AM": "ten fifteen am",
    }
    value = text
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"[\"“”.,;:?!]", "", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    prefix = rng.choice(["", "um ", "so ", "okay "])
    return prefix + value


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(SEED)
    records: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    base_time = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
    for project_index, project in enumerate(PROJECTS):
        project_id, name, owner, reviewer, ticket = project
        projects.append(
            {
                "id": project_id,
                "name": name,
                "aliases": [name.removeprefix("Project ")],
                "owner": owner,
                "reviewer": reviewer,
                "internal_ticket": ticket,
            }
        )
        project_scenarios = scenarios(project, project_index)
        if len(project_scenarios) != 25:
            raise AssertionError("each project must produce exactly 25 scenarios")
        for slot, scenario in enumerate(project_scenarios):
            take_id = f"take_{project_index * 25 + slot + 1:04d}"
            event_ts = base_time + timedelta(days=project_index, hours=slot * 2)
            resolved_project = project_id if scenario.scoped else None
            record = {
                "take_id": take_id,
                "raw_asr": raw_asr(scenario.text, rng),
                "formatted_text": scenario.text,
                "source_application": APPLICATIONS[(project_index + slot) % len(APPLICATIONS)],
                "event_ts": event_ts.isoformat().replace("+00:00", "Z"),
                "project_id": resolved_project,
                "metadata": {
                    "project_id": resolved_project,
                    "project_name": name if resolved_project else None,
                    "scenario_type": scenario.category,
                    "window_title": f"{name} working notes" if resolved_project else "Personal notes",
                    "generation_version": GENERATION_VERSION,
                },
            }
            TakeCreate.model_validate(record)
            records.append(record)
            expected_memories = []
            if scenario.should_create_memory:
                expected_memories.append(
                    {
                        "memory_type": scenario.memory_type,
                        "epistemic_status": scenario.epistemic_status,
                        "subject": scenario.subject,
                        "predicate": scenario.predicate,
                        "object_value": scenario.object_value,
                        "supersedes_take_id": (
                            f"take_{project_index * 25 + scenario.supersedes_slot + 1:04d}"
                            if scenario.supersedes_slot is not None
                            else None
                        ),
                    }
                )
            labels.append(
                {
                    "take_id": take_id,
                    "project_id": resolved_project,
                    "scenario_type": scenario.category,
                    "should_create_memory": scenario.should_create_memory,
                    "deletion_sentinel": scenario.deletion_sentinel,
                    "expected_memories": expected_memories,
                }
            )
    if len(records) != 500 or len({record["take_id"] for record in records}) != 500:
        raise AssertionError("generator must produce exactly 500 uniquely identified records")
    return records, labels, projects


def jsonl(items: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items)


def canonical_text_sha256(content: str) -> str:
    """Hash UTF-8 text after normalizing platform line endings to canonical LF."""
    canonical_content = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()


def generate_outputs() -> dict[str, str]:
    records, labels, projects = build()
    corpus_text = jsonl(records)
    labels_text = jsonl(labels)
    projects_text = json.dumps(projects, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    category_counts = Counter(label["scenario_type"] for label in labels)
    manifest = {
        "generation_version": GENERATION_VERSION,
        "seed": SEED,
        "record_count": len(records),
        "project_count": len(projects),
        "records_per_project": 25,
        "hash_contract": "UTF-8 text with line endings normalized to LF",
        "category_counts": dict(sorted(category_counts.items())),
        "corpus_sha256": canonical_text_sha256(corpus_text),
        "gold_labels_sha256": canonical_text_sha256(labels_text),
        "projects_sha256": canonical_text_sha256(projects_text),
    }
    return {
        "kivi_500.jsonl": corpus_text,
        "gold_labels.jsonl": labels_text,
        "projects.json": projects_text,
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the deterministic Kivi 500-record corpus")
    parser.add_argument("--check", action="store_true", help="verify committed outputs without rewriting them")
    args = parser.parse_args()
    output_dir = Path(__file__).resolve().parent
    outputs = generate_outputs()
    if args.check:
        mismatches = [name for name, content in outputs.items() if not (output_dir / name).exists() or (output_dir / name).read_text(encoding="utf-8") != content]
        if mismatches:
            raise SystemExit(f"corpus outputs are stale or missing: {', '.join(mismatches)}")
        print("Corpus verification passed: 500 deterministic records and matching hashes.")
        return
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8", newline="\n")
    print("Generated 500 records, gold labels, projects, and deterministic manifest.")


if __name__ == "__main__":
    main()
