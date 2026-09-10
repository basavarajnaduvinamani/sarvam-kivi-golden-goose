from enum import StrEnum


class EpistemicStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    UNRESOLVED = "UNRESOLVED"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"
    TOMBSTONED = "TOMBSTONED"


class MemoryType(StrEnum):
    DECISION = "decision"
    CONSTRAINT = "constraint"
    COMMITMENT = "commitment"
    CORRECTION = "correction"
    REJECTED_PROPOSAL = "rejected_proposal"
    CONDITION = "condition"
    UNRESOLVED_QUESTION = "unresolved_question"
    EPISODE = "episode"
    PREFERENCE = "preference"


class QueryStatus(StrEnum):
    ANSWERED = "ANSWERED"
    NO_EVIDENCE = "NO_EVIDENCE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    SERVICE_ERROR = "SERVICE_ERROR"


class PurgeStatus(StrEnum):
    PENDING = "pending"
    PURGED = "purged"
    FAILED = "failed"

