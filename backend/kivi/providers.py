from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .schemas import AnswerClaim, ExtractionDecision, MemoryRead, TakeCreate


class ProviderUsage(BaseModel):
    model_name: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0, ge=0)


class ExtractionResult(BaseModel):
    decision: ExtractionDecision
    usage: ProviderUsage


class EmbeddingResult(BaseModel):
    vector: list[float]
    usage: ProviderUsage


class GroundedAnswer(BaseModel):
    answer: str
    claims: list[AnswerClaim]
    usage: ProviderUsage


class MemoryExtractor(Protocol):
    def extract(self, take: TakeCreate, project_name: str) -> ExtractionResult: ...


class Embedder(Protocol):
    def embed(self, text: str) -> EmbeddingResult: ...


class GroundedAnswerer(Protocol):
    def answer(self, question: str, memories: list[MemoryRead]) -> GroundedAnswer: ...


class ProviderUnavailable(RuntimeError):
    """Raised when a required model provider cannot complete a request."""

