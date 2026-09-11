from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from ..providers import EmbeddingResult, ExtractionResult, GroundedAnswer, ProviderUnavailable, ProviderUsage
from ..schemas import AnswerClaim, EvidenceCandidate, ExtractionDecision, MemoryCandidate, MemoryRead, TakeCreate


ROOT = Path(__file__).resolve().parents[3]


def memory_id_for_take(take_id: str, index: int = 0, schema_version: str = "1.0") -> str:
    stable_key = f"{take_id}|{index}|{schema_version}"
    return f"mem_{hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:32]}"


class GoldExtractor:
    """Offline extraction fixture backed by committed, reviewer-inspectable gold labels."""

    def __init__(self, labels_path: Path | None = None) -> None:
        path = labels_path or ROOT / "corpus" / "gold_labels.jsonl"
        self.labels = {
            item["take_id"]: item
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
            for item in [json.loads(line)]
        }

    def extract(self, take: TakeCreate, project_name: str) -> ExtractionResult:
        label = self.labels[take.take_id]
        memories: list[MemoryCandidate] = []
        for item in label["expected_memories"]:
            supersedes_take_id = item.get("supersedes_take_id")
            memories.append(
                MemoryCandidate(
                    memory_type=item["memory_type"],
                    subject=item["subject"],
                    predicate=item["predicate"],
                    object_value=item["object_value"],
                    epistemic_status=item["epistemic_status"],
                    confidence=1.0,
                    supersedes_memory_id=memory_id_for_take(supersedes_take_id) if supersedes_take_id else None,
                    evidence=[
                        EvidenceCandidate(
                            span_start=0,
                            span_end=len(take.formatted_text),
                            required=True,
                            sufficiency_contribution="The complete labelled statement supports this memory.",
                        )
                    ],
                )
            )
        decision = ExtractionDecision(
            memories=memories,
            ignored_reason=None if memories else "The gold label intentionally excludes this background-noise take.",
        )
        return ExtractionResult(decision=decision, usage=ProviderUsage(model_name="deterministic-gold-extractor"))


_STOPWORDS = {
    "a", "an", "and", "at", "be", "for", "from", "in", "is", "it", "of", "on", "or", "project",
    "the", "this", "to", "what", "when", "where", "who", "with",
}
_CONCEPTS = {
    "schedule": "review", "scheduled": "review", "slot": "review", "time": "review",
    "working": "draft", "location": "draft", "document": "draft",
    "owner": "owns", "demonstration": "demo", "demo": "demo",
    "validation": "recovery", "reviewer": "recovery",
    "database": "production", "db": "production",
    "setting": "preference", "style": "preference",
    "ticket": "identifier", "id": "identifier",
    "delete": "deletion", "archive": "archival", "logs": "archival",
    "ship": "shipment", "moved": "delay", "week": "delay",
    "style": "format", "writing": "format", "prefers": "preference", "prefer": "preference",
}
_INTENT_FEATURES = {
    "archival", "conditional", "counterfactual", "demo", "deployment", "draft", "format",
    "hypothetical", "identifier", "owns", "preference", "production", "recovery", "rejected", "review", "shipment",
}


def _features(text: str) -> set[str]:
    tokens = re.findall(r"[\w.-]+", text.casefold(), flags=re.UNICODE)
    return {_CONCEPTS.get(token, token) for token in tokens if token not in _STOPWORDS and len(token) > 1}


class DeterministicEmbedder:
    dimensions = 512

    def embed(self, text: str) -> EmbeddingResult:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for feature in _features(text):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 3.0 if feature in _INTENT_FEATURES else 1.0
        if not vector.any():
            vector[0] = 1.0
        vector /= np.linalg.norm(vector)
        return EmbeddingResult(
            vector=vector.tolist(),
            usage=ProviderUsage(model_name="deterministic-hash-embedding"),
        )


class DeterministicAnswerer:
    def answer(self, question: str, memories: list[MemoryRead]) -> GroundedAnswer:
        question_features = _features(question)
        ranked = sorted(
            memories,
            key=lambda memory: len(question_features & _features(f"{memory.predicate} {memory.object_value}")),
            reverse=True,
        )
        best = len(question_features & _features(f"{ranked[0].predicate} {ranked[0].object_value}"))
        selected = [
            memory for memory in ranked
            if len(question_features & _features(f"{memory.predicate} {memory.object_value}")) >= max(1, best - 1)
        ]
        if not selected:
            selected = ranked[:1]
        claims: list[AnswerClaim] = []
        sentences: list[str] = []
        for memory in selected:
            status = memory.epistemic_status.value.casefold()
            claim = f"{memory.subject}: {memory.predicate} is {memory.object_value} ({status})."
            take_ids = sorted({item.take_id for item in memory.evidence if item.is_required})
            sentences.append(claim)
            claims.append(AnswerClaim(claim_text=claim, memory_ids=[memory.id], supporting_take_ids=take_ids))
        answer = " ".join(sentences)
        return GroundedAnswer(
            answer=answer,
            claims=claims,
            usage=ProviderUsage(
                model_name="deterministic-grounded-answerer",
                input_tokens=len(question.split()) + sum(len(item.object_value.split()) for item in memories),
                output_tokens=len(answer.split()),
                estimated_cost_usd=0.0,
            ),
        )


class FailingEmbedder:
    def embed(self, text: str) -> EmbeddingResult:
        raise ProviderUnavailable("deterministic service-outage fixture")
