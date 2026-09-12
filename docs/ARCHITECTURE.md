# Kivi Architecture

Kivi is a voice-first semantic memory system engineered to turn spoken dictations across desktop applications into durable, project-scoped understanding. The core architectural principle separates deterministic memory lifecycle controls, epistemic boundaries, and evidence invariants from stochastic foundation model generation.

```
+-----------------------------------------------------------------------------------+
|                                 1. CAPTURE                                        |
|  Demonstrated via client- / corpus-supplied Takes with source_application tags    |
|  Captures: Raw ASR, Formatted Text, Source Application, Timestamp, Metadata       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                                2. INGESTION                                       |
|  Deduplication by Take ID | Vector Embedding (BLOB) | Unscoped Inbox Staging      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                                3. EXTRACTION                                      |
|  Structured Extraction (Deterministic / Model) -> MemoryType & EpistemicStatus    |
|  Character Span Evidence Offsets (span_start, span_end, is_required)              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                                 4. STORAGE                                        |
|  SQLite + SQLAlchemy ORM + Alembic Migrations                                     |
|  Tables: projects, takes, memories, memory_evidence, tombstones, query_runs,      |
|          query_claims, memory_fts (SQLite FTS5 virtual table with triggers)       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                              5. SCOPED RETRIEVAL                                  |
|  - Strict Project Isolation (no cross-project contamination)                      |
|  - Lifecycle Gating (ACTIVE only) & Epistemic Filtering                           |
|  - Evidence Gating (all required takes must be non-deleted)                       |
|  - Hybrid Ranking: 0.88 * Cosine Similarity + 0.12 * FTS5 Keyword Score           |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                      6. TYPED ANSWERS & GROUNDED REASONING                        |
|  QueryStatus: ANSWERED | NO_EVIDENCE | NEEDS_CLARIFICATION |                      |
|               CONFLICTING_EVIDENCE | SERVICE_ERROR                                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------+-----------------------------------------+
|                       7. PROVENANCE & CITATION AUDIT                              |
|  Every QueryClaim verified against locked evidence package & supporting takes     |
+-----------------------------------------------------------------------------------+
        |                                                           |
        v                                                           v
+---------------------------------------+   +---------------------------------------+
|      8. CORRECTION & SUPERSESSION     |   |      9. TWO-PHASE DELETION            |
|  ACTIVE -> SUPERSEDED (valid_to = ts) |   |  Phase 1: Tombstone & Invalidate      |
|  New CORRECTION memory created        |   |  Phase 2: Purge payload & Verify      |
+---------------------------------------+   +---------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                               10. EVALUATION                                      |
|  132-Case Canonical Deterministic Suite (evalrun_3bb3ebb25f16, 100% pass)         |
|  Candidate Provider Evaluation Harness (live LLM evaluation)                      |
+-----------------------------------------------------------------------------------+
```

---

## The 10 Lifecycle Stages

### 1. Capture
The capture boundary operates at the interface between the user's speech and desktop applications. While Kivi's ultimate product direction envisions ambient desktop integration, this repository demonstrates memory workflows through client- or corpus-supplied records rather than direct OS foreground window capture. When dictation records are received, Kivi stores each utterance as a **retained source Take** (`Take` model in [backend/kivi/models.py](../backend/kivi/models.py)):
- `id`: Unique identifier for the dictation event.
- `raw_asr`: Exact phonetic or automated speech recognition transcript.
- `formatted_text`: Cleaned, punctuation-formatted transcript text.
- `source_application`: Declared identifier of the originating application (e.g., `"Slack"`, `"VS Code"`, `"Email"`).
- `event_ts`: Timestamp when the user spoke the utterance.
- `source_metadata`: Declared application context, channel/file names, and surrounding tags.

Ordinary dictation produces text inside the user's active application. In this repository, the retained source Take preserves this input for semantic processing while keeping payload fields mutable so two-phase deletion can redact sensitive data upon request.

### 2. Ingestion Pipeline
The ingestion service ([backend/kivi/services/ingestion.py](../backend/kivi/services/ingestion.py)) processes incoming takes through strict validation and staging gates:
- **Deduplication & Integrity**: Enforces uniqueness on `take_id` to prevent duplicate writes.
- **Vector Embedding**: Computes dense vector representations using the configured `Embedder` protocol. Vectors are stored directly as binary BLOBs (`LargeBinary`) in SQLite via NumPy serialization (`vector_to_blob` in [backend/kivi/serialization.py](../backend/kivi/serialization.py)).
- **Project Scoping & Inbox Staging**: Takes with confirmed project identifiers proceed to semantic extraction. Takes with unresolved project associations (`project_id = None`) are safely committed to the database and routed to the **Inbox** (`/inbox`), allowing the user to explicitly assign project scope before any derived memories are extracted.

### 3. Semantic Extraction
Once project scope is confirmed, the extraction engine invokes a `MemoryExtractor` provider (deterministic rule-based or model structured output):
- **Memory Types** (`MemoryType` enum in [backend/kivi/enums.py](../backend/kivi/enums.py)):
  - `DECISION`: Concrete conclusions reached for a project.
  - `CONSTRAINT`: Inflexible requirements, boundary conditions, or architectural rules.
  - `COMMITMENT`: Assigned actions, promises, or owner deliverables.
  - `CORRECTION`: Explicit updates overriding earlier statements.
  - `REJECTED_PROPOSAL`: Ideas or options explicitly rejected during discussion.
  - `CONDITION`: Contingent requirements dependent on external outcomes.
  - `UNRESOLVED_QUESTION`: Open queries or unresolved ambiguities.
  - `EPISODE`: Specific factual occurrences or historical event summaries.
  - `PREFERENCE`: Enduring user or team preferences (e.g., formatting, tooling).
- **Epistemic States** (`EpistemicStatus` enum): `PROPOSED`, `APPROVED`, `REJECTED`, `CONDITIONAL`, `UNRESOLVED`.
- **Evidence Binding**: Every extracted memory record links back to the originating take with character span offsets (`span_start`, `span_end`), an `evidence_role` label, an `is_required` flag, and a rationale for sufficiency.

### 4. Storage & Relational Schema
Kivi relies on a normalized relational schema backed by SQLite and managed via SQLAlchemy 2.0 with Alembic database migrations ([alembic/versions/](../alembic/versions)):
- `projects`: Project ID, unique name, JSON aliases, and timestamps.
- `takes`: Retained source take records, raw ASR, formatted text, source application, timestamp, JSON metadata, BLOB embedding, soft-deletion flag (`is_deleted`), and tombstone timestamp.
- `memories`: Normalized semantic units with `project_id`, `memory_type`, `subject`, `predicate`, `object_value`, `epistemic_status`, `lifecycle_status`, temporal validity boundaries (`valid_from`, `valid_to`), confidence score, extraction provenance, and `supersedes_memory_id`.
- `memory_evidence`: Join table enforcing unique spans (`memory_id`, `take_id`, `span_start`, `span_end`) and recording evidence necessity (`is_required`).
- `tombstones`: Two-phase deletion audit records (`take_id`, `purge_status`, `created_at`, `purged_at`, `verified_at`, `failure_detail`).
- `query_runs`: Complete execution log of every Hey Kivi interaction, recording question, typed status, answer, decision reason, latency breakdowns, model usage, token counts, and estimated cost.
- `query_claims`: Granular claim-level evidence linkages binding every answered statement to memory IDs and supporting take IDs.
- `memory_fts`: Dedicated SQLite FTS5 virtual table indexing subject, predicate, and object values with automated database triggers for `INSERT`, `UPDATE`, and `DELETE`.

### 5. Scoped Retrieval
Retrieval ([backend/kivi/services/retrieval.py](../backend/kivi/services/retrieval.py)) executes under rigid deterministic filters before scoring relevance:
1. **Scope Boundary Enforcement**: Retrieval requires an explicit `project_id`. If omitted, or if the question explicitly refers to a different registered project name or alias, retrieval halts and returns `NEEDS_CLARIFICATION`. Semantic similarity alone is never permitted to cross project boundaries.
2. **Lifecycle & Epistemic Gating**: Only memories with `lifecycle_status == ACTIVE` and answerable epistemic states (`APPROVED`, `REJECTED`, `CONDITIONAL`, `PROPOSED`, `UNRESOLVED`) are considered.
3. **Required Evidence Invariant**: Every candidate memory is inspected against its linked evidence. If any required supporting take has been marked deleted (`take.is_deleted == True`) or lacks an embedding, the memory is dropped from candidate consideration.
4. **Hybrid Scoring**:
   $$\text{Score} = 0.88 \times \text{CosineSimilarity}(\text{take\_embedding}, \text{query\_embedding}) + 0.12 \times (\text{FTS5 Match Boost})$$
5. **Threshold Filter**: Only the top 5 candidates with a score exceeding the similarity threshold (default $0.45$) are selected. If no candidates pass, retrieval halts with `NO_EVIDENCE`.

### 6. Typed Answers & Epistemic Safety
Unlike unstructured RAG chat interfaces that hallucinate plausible answers when information is missing, Hey Kivi enforces structured response types governed by the `QueryStatus` contract ([backend/kivi/enums.py](../backend/kivi/enums.py)):
- `ANSWERED`: Sufficient, uncontradicted evidence exists in the locked evidence package to fully answer the query.
- `NO_EVIDENCE`: No active memory passed project, lifecycle, evidence, or relevance gates. Kivi explicitly abstains instead of fabricating an answer.
- `NEEDS_CLARIFICATION`: The query references an ambiguous, missing, or conflicting project scope.
- `CONFLICTING_EVIDENCE`: Multiple active, approved memories disagree on a subject and predicate without a valid supersession relationship. Rather than guessing, Kivi surfaces the conflict and abstains from picking a winner.
- `SERVICE_ERROR`: Upstream model failure or citation validation rejection.

### 7. Provenance & Citation Auditing
Kivi enforces verifiable citation integrity before an answer can be returned:
- The answerer must return claims paired with specific memory IDs and supporting take IDs.
- Every claim is validated against the locked evidence package:
  - All cited memory IDs must belong to the retrieved set.
  - All cited take IDs must belong to the permitted takes supporting those memories.
  - All takes marked `is_required` by the underlying memory evidence must be explicitly cited by the claim.
- Any uncited assertion or omitted required citation causes immediate rejection with a `SERVICE_ERROR` status; unsupported or citation-invalid generated claims are rejected by the validation policy.

### 8. Correction & Supersession
Knowledge evolves over time. Kivi handles corrections through a deterministic state machine ([backend/kivi/services/memory_control.py](../backend/kivi/services/memory_control.py)):
- When a correction is submitted (via dictation or the Timeline Inspector), Kivi creates a new `Take` documenting the user-confirmed correction.
- The pre-existing memory transitions from `ACTIVE` to `SUPERSEDED`, and its temporal boundary `valid_to` is stamped with the correction timestamp.
- A new `ACTIVE` memory of type `CORRECTION` is inserted with `supersedes_memory_id` pointing directly to the superseded record.
- Historical records remain intact for timeline auditability, but subsequent retrieval queries strictly ignore `SUPERSEDED` records in favor of current active understanding.

### 9. Two-Phase Deletion & Tombstoning
Deletion integrity is critical when dealing with private or sensitive user dictation ([backend/kivi/services/deletion.py](../backend/kivi/services/deletion.py)):
- **Phase 1: Durable Logical Tombstone**:
  - The target take is flagged `is_deleted = True` and timestamped (`tombstoned_at = now()`).
  - A `Tombstone` record is created with `purge_status = PENDING`.
  - All downstream memories depending on this take via `memory_evidence` immediately transition from `ACTIVE` to `INVALIDATED`.
  - This step commits immediately, ensuring the take and its memories become unqueryable even if subsequent operations fail.
- **Phase 2: Physical Payload Purge & Exclusion Verification**:
  - The take's sensitive contents (`raw_asr`, `formatted_text`, `embedding`, `source_metadata`) are cleared to `NULL` / empty dict.
  - `tombstone.purge_status` transitions to `PURGED`.
  - An automated verification check (`_verify_exclusion`) executes: it verifies that all removable content is gone and confirms that no active memory in the database links to the deleted take.
  - Upon successful verification, `tombstone.verified_at` is stamped.

### 10. Evaluation Subsystem
Kivi incorporates a complete, reproducible evaluation harness ([backend/kivi/evaluation/runner.py](../backend/kivi/evaluation/runner.py)):
- **Deterministic Evaluation Suite**: Runs offline against 500 corpus records (`corpus/kivi_500.jsonl`) across 132 test cases (`evaluation/cases.jsonl`). It exercises all 11 evaluation categories (project isolation, deletion integrity, conflict detection, epistemic safety, temporal correction, cross-application recovery, multilingual identifiers, etc.) without external API dependencies or costs.
- **Candidate Evaluation Mode**: Executes the identical 132 test cases using real foundation models (the configured OpenAI model and embedding model) to evaluate open-ended reasoning, extraction nuance, and live answering fidelity.
- **Comprehensive Reporting**: Evaluates latency percentiles (p50, p95), database storage growth, token consumption, and dollar costs, writing machine-readable JSON (`results/latest.json`) and Markdown summaries (`results/latest.md`).

---

## Technology Stack

| Layer | Component | Description |
|---|---|---|
| **Runtime & Language** | Python 3.11+ | Type-annotated, modern Python architecture |
| **Web Framework** | FastAPI & Uvicorn | High-performance asynchronous REST and SSR web service |
| **CLI Framework** | Python `argparse` | Canonical command-line entrypoint (`kivi`) |
| **Persistence ORM** | SQLAlchemy 2.0 | Explicit relational modeling, transactions, and unit-of-work |
| **Relational Database** | SQLite | Serverless, zero-configuration, reproducible local database |
| **Database Migrations** | Alembic | Tracked, reversible schema migration scripts |
| **Full-Text Search** | SQLite FTS5 | Virtual full-text indexing with `unicode61` tokenizer and automated triggers |
| **Vector Similarity** | NumPy | In-process dot-product cosine similarity over float32 BLOB vectors |
| **Frontend & UI** | Jinja2 & HTMX | Server-rendered Jinja2 templates with HTMX interactions |
| **CSS & Design System** | Vanilla CSS | Tokens aligned with [DESIGN_SYSTEM.md](../DESIGN_SYSTEM.md) |
| **Testing & Evaluation** | Pytest & Custom Runner | Suite of automated tests and comprehensive 132-case evaluation engine |
