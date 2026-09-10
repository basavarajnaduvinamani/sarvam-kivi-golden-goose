from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from kivi.cli import load_corpus
from corpus.generate_corpus import canonical_text_sha256, generate_outputs


CORPUS_DIR = Path(__file__).parents[1] / "corpus"


def test_committed_corpus_is_exactly_500_unique_deterministic_records():
    records = load_corpus(CORPUS_DIR / "kivi_500.jsonl", 500)
    labels = [json.loads(line) for line in (CORPUS_DIR / "gold_labels.jsonl").read_text(encoding="utf-8").splitlines()]
    projects = json.loads((CORPUS_DIR / "projects.json").read_text(encoding="utf-8"))
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    generated = generate_outputs()
    assert len(records) == len(labels) == 500
    assert len({record.take_id for record in records}) == 500
    assert len(projects) == 20
    assert Counter(label["scenario_type"] for label in labels) == Counter(manifest["category_counts"])
    assert all(count == 20 for count in manifest["category_counts"].values())
    assert {record.project_id for record in records if record.project_id} == {project["id"] for project in projects}
    assert manifest["hash_contract"] == "UTF-8 text with line endings normalized to LF"
    for filename, key in (("kivi_500.jsonl", "corpus_sha256"), ("gold_labels.jsonl", "gold_labels_sha256"), ("projects.json", "projects_sha256")):
        committed_text = (CORPUS_DIR / filename).read_text(encoding="utf-8")
        assert committed_text == generated[filename]
        assert canonical_text_sha256(committed_text) == manifest[key]


def test_corpus_contains_required_adversarial_categories():
    labels = [json.loads(line) for line in (CORPUS_DIR / "gold_labels.jsonl").read_text(encoding="utf-8").splitlines()]
    categories = {label["scenario_type"] for label in labels}
    assert {"schedule_correction", "rejected_proposal", "conditional_action", "semantic_leakage_trap", "deletion_sentinel", "hindi_code_switch", "kannada_code_switch", "background_noise"} <= categories
    assert sum(label["deletion_sentinel"] for label in labels) == 20
    assert sum(not label["should_create_memory"] for label in labels) == 20


def test_manifest_hash_is_identical_for_lf_and_crlf_checkouts():
    canonical = "first record\nsecond record\n"
    windows_checkout = canonical.replace("\n", "\r\n")
    assert canonical_text_sha256(windows_checkout) == canonical_text_sha256(canonical)
