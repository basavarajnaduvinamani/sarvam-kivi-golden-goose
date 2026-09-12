# Kivi Semantic Memory System

**For multilingual knowledge workers who dictate decisions across desktop applications, Kivi is a voice-first, project-scoped memory that turns intentional speech into a traceable record of what was decided, revised, rejected, or left open.**

Where ordinary dictation ends at formatted text inside an active application window, Kivi establishes durable semantic memory to power **Hey Kivi**—allowing users to recall project state, retrieve exact citations across applications, apply temporal corrections, and safely purge sensitive evidence.

## Reviewer map

| Concept & Product | Technical Specifications | Evidence & Proof |
|---|---|---|
| [Product Positioning](docs/positioning_statement.md) | [Architecture Blueprint](docs/ARCHITECTURE.md) | [Reviewer Runbook](RUN.md) |
| [Product Vision](docs/vision_document.md) | [Design System](DESIGN_SYSTEM.md) | [Browser Evidence Gallery](evidence/browser/GALLERY.md) |
| [System Limitations](docs/LIMITATIONS.md) | [API Integration Contract](docs/API_CONTRACT.md) | [Research & Audit Index](research/README.md) |
| [Documentation Map](docs/README.md) | | [Latest Evaluation Results](results/latest.md) |

## Why this repository is evidence-led

This submission relies on observable behavior and reproducible data rather than theoretical capability:
- **Reproducible Evaluation**: A [500-record JSONL corpus](corpus/kivi_500.jsonl) drives a [132-case deterministic evaluation suite](evaluation/cases.jsonl) proving zero leakage, zero resurrection, and zero citation failures.
- **Empirical Grounding**: The product vision and architectural constraints respond directly to [46 live audit cases](research/empirical_audit/KIVI_WINDOWS_AUDIT_REPORT.md) performed on the Kivi Windows alpha application.
- **Visual Verification**: The [browser gallery](evidence/browser/GALLERY.md) captures real local flows demonstrating strict lifecycle and provenance guarantees.

---


## Concrete Use Cases

While Kivi's product vision addresses ambient desktop computing across applications, this repository implements and evaluates semantic memory through client- or corpus-supplied takes bearing `source_application` metadata. The repository does not capture Slack, VS Code, email, meetings, or foreground windows directly.

The five core workflows demonstrated by this implementation are:

1. **Cross-Application Context Recovery**
   *Workflow*: A user imports or submits takes tagged with different `source_application` metadata (e.g., `Slack` and `VS Code`) under a common project scope (e.g., database migration).
   *Demonstrated Behavior*: When querying Hey Kivi with a related question, the system retrieves active decisions supported by takes across both application sources because they share the same explicit project_id, demonstrating cross-application context recovery without cross-project leakage.

2. **Contextual Briefing and Status Recovery**
   *Workflow*: A user requests a briefing on project status before a meeting, querying active commitments and open questions.
   *Demonstrated Behavior*: Kivi evaluates active memories within the project scope. If decisions and conditions are approved, it returns a grounded answer citing supporting takes. If no verified evidence exists, Kivi explicitly returns `NO_EVIDENCE` rather than fabricating plausible progress.

3. **Explicit Temporal Correction and Supersession**
   *Workflow*: An earlier take approves a schedule or specification, and a subsequent take or Inspector action submits a correction (e.g., moving deployment from Friday to Tuesday).
   *Demonstrated Behavior*: The system updates the earlier memory's status to `SUPERSEDED` (`valid_to = event_ts`) and creates a new `ACTIVE` correction record. Future queries return the current value, while the `/timeline` interface preserves the full auditable lineage.

4. **Multilingual Knowledge Work (Indic Code-Switching)**
   *Workflow*: Dictation records containing mixed Indic and English phrasing (e.g., Kannada or Hindi-English code-switching) are imported into the repository.
   *Demonstrated Behavior*: The system preserves supplied code-switched transcripts and evaluates structured extraction on committed fixtures, and indexes text in SQLite FTS5 using the `unicode61` tokenizer.

5. **Verifiable Two-Phase Deletion and Epistemic Invalidation**
   *Workflow*: A user deletes a sensitive or confidential take via the API or interface.
   *Demonstrated Behavior*: Phase 1 durably tombstones the take and immediately marks all dependent derived memories `INVALIDATED`. Phase 2 purges mutable payload fields (`raw_asr`, `formatted_text`, `embedding`, `source_metadata`) and verifies exclusion. Subsequent queries, index rebuilds, and restarts cannot resurrect the redacted information.

---

## Architecture Overview

Kivi's architecture strictly separates deterministic memory lifecycle and epistemic controls from stochastic foundation model generation. The system covers 10 sequential lifecycle stages:

1. **Capture**: Records raw ASR text, LLM-formatted text, source application name, client timestamp, and metadata into retained source `Take` records.
2. **Ingestion**: Validates uniqueness, generates vector embeddings (stored as binary BLOBs), and stages unscoped takes in the `/inbox` for user-directed project assignment.
3. **Semantic Extraction**: Maps project-scoped takes into structured memory types (`DECISION`, `CONSTRAINT`, `COMMITMENT`, `CORRECTION`, `REJECTED_PROPOSAL`, `CONDITION`, `UNRESOLVED_QUESTION`, `EPISODE`, `PREFERENCE`) with epistemic statuses (`PROPOSED`, `APPROVED`, `REJECTED`, `CONDITIONAL`, `UNRESOLVED`) and optional character span offsets (`span_start`, `span_end`).
4. **Storage**: Relational SQLite database managed via SQLAlchemy 2.0 and Alembic migrations (`projects`, `takes`, `memories`, `memory_evidence`, `tombstones`, `query_runs`, `query_claims`, and SQLite FTS5 `memory_fts`).
5. **Scoped Retrieval**: Hard project isolation gates queries. Applies active lifecycle filtering, required evidence exclusion, and hybrid scoring:
   $$\text{Score} = 0.88 \times \text{CosineSimilarity} + 0.12 \times \text{FTS5KeywordScore}$$
6. **Typed Answers**: Replaces unconstrained chat with strict `QueryStatus` types: `ANSWERED`, `NO_EVIDENCE`, `NEEDS_CLARIFICATION`, `CONFLICTING_EVIDENCE`, and `SERVICE_ERROR`. Kivi returns typed abstention states when policy conditions are unmet and rejects unsupported or citation-invalid generated claims.
7. **Provenance & Citation Auditing**: Every answer claim is verified against the locked evidence package; unsupported or citation-invalid generated claims are rejected by the validation policy.
8. **Correction & Supersession**: Automatic and user-directed state transitions (`ACTIVE` $\rightarrow$ `SUPERSEDED`) maintain timeline lineage while preventing stale facts from polluting active queries.
9. **Two-Phase Deletion**: Phase 1 durably tombstones takes and invalidates dependent memories; Phase 2 purges payload data and verifies exclusion across all indexes and query paths.
10. **Evaluation Subsystem**: Full evaluation harness supporting offline deterministic verification and live candidate model evaluation with latency, token, and cost metrics.

For complete architectural details, schemas, and sequence flows, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Evaluation Results

Kivi includes a dual-track evaluation harness ([backend/kivi/evaluation/runner.py](backend/kivi/evaluation/runner.py)) operating on a 500-record development corpus ([corpus/kivi_500.jsonl](corpus/kivi_500.jsonl)) and 132 test cases ([evaluation/cases.jsonl](evaluation/cases.jsonl)).

### Canonical Deterministic Evaluation (132/132 Passed)

The repository's committed benchmark result is the **canonical deterministic evaluation** ([results/latest.md](results/latest.md), [results/latest.json](results/latest.json)):

- **Run ID**: `evalrun_3bb3ebb25f16`
- **Evaluation Mode**: `deterministic` (offline, reproducible, zero API cost)
- **Total Cases**: 132 | **Passed**: 132 | **Failed**: 0 | **Pass Rate**: 100.0%

| Category | Passed | Total | Pass Rate | Key Invariant Verified |
|---|---:|---:|---:|---|
| `abstention_and_scope` | 12 | 12 | 100.0% | Abstains with `NO_EVIDENCE` / `NEEDS_CLARIFICATION` when evidence or scope is missing |
| `cross_application_recovery` | 12 | 12 | 100.0% | Recovers facts spanning multiple desktop applications under the same project |
| `deletion_integrity` | 12 | 12 | 100.0% | Verifies tombstoning, invalidation, payload purging, and zero resurrection after FTS rebuild |
| `distributed_evidence` | 12 | 12 | 100.0% | Assembles multi-take evidence packages requiring conjunction of multiple dictations |
| `epistemic_safety` | 12 | 12 | 100.0% | Prevents promoting `PROPOSED`, `REJECTED`, or `CONDITIONAL` statements into active facts |
| `multilingual_identifiers` | 12 | 12 | 100.0% | Preserves Indic code-switching and technical identifiers without corruption |
| `preference_precedence` | 12 | 12 | 100.0% | Verifies application-specific preferences override general defaults deterministically |
| `project_isolation` | 12 | 12 | 100.0% | Zero cross-project leakage; queries to Project A never access Project B evidence |
| `provenance` | 12 | 12 | 100.0% | Rejects any response lacking required supporting Take IDs or valid provenance |
| `service_and_conflict` | 12 | 12 | 100.0% | Returns `CONFLICTING_EVIDENCE` on unmerged conflicts; handles provider service errors |
| `temporal_correction` | 12 | 12 | 100.0% | Honors `SUPERSEDED` state; returns current active replacement rather than outdated facts |

- **Performance & Invariants**:
  - Cross-project leakage count: **0**
  - Deleted memory resurrection count: **0**
  - Invalid citation count: **0**
  - Fabricated answer count: **0**
  - Retrieval latency (p50 / p95): **3.0 ms / 3.0 ms**
  - End-to-end latency (p50 / p95): **4.0 ms / 4.0 ms**
  - Database growth across 500-take evaluation: **2,723,840 bytes**
  - Execution cost: **$0.00**

### Candidate Provider Evaluation (Unexecuted Baseline)

Kivi also implements a **candidate evaluation mode** (`kivi evaluate --mode candidate`). This mode connects the pipeline to live foundation models (the configured OpenAI model and embedding model) to test open-domain phrasing, model extraction nuance, and generative reasoning.

> [!IMPORTANT]
> **Candidate mode has not yet been executed in this repository submission.**
> Running candidate mode requires setting `OPENAI_API_KEY` in `.env` and supplying external compute budget. Reviewers wishing to evaluate live model behavior can execute candidate evaluation using the documented instructions in [RUN.md](RUN.md).

---

## Limitations

Kivi is deliberately scoped to demonstrate core semantic memory integrity rather than general enterprise SaaS infrastructure. Key technical limitations include:

- **Single-Tenant Identity**: Memory is partitioned by project scope for a single user; multi-user authorization and cryptographic tenant segregation are not implemented.
- **Synchronous Pipeline**: Ingestion, vector embedding, and query answering execute synchronously within FastAPI request handlers. There is no asynchronous distributed task queue.
- **Storage & Search Scale**: Embeddings are stored as SQLite BLOBs with in-process NumPy cosine similarity scoring ($O(N)$ linear scan), optimized for ~500–1,000 takes rather than large-scale enterprise vector indexes.
- **Application Context Reporting**: Source applications are identified via client-reported metadata rather than automated desktop OS window focus hooks.
- **Deterministic vs. Live Fluency**: The 132-case deterministic evaluation verifies structural and epistemic invariants, not natural language conversational elegance.

For a detailed analysis of architectural boundaries, see [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

---

## Quick Start and Reviewer Operations

Please refer to [RUN.md](RUN.md) for the primary review method and step-by-step reproduction instructions:

1. **Setup**: Create Python 3.11+ virtual environment, install dependencies (`pip install -e .`), and copy `.env.example` to `.env`.
2. **Database Migration**: Initialize SQLite schema with `kivi db migrate`.
3. **Corpus Import**: Import project registry and 500-record corpus with `kivi projects import corpus/projects.json` and `kivi corpus import corpus/kivi_500.jsonl`.
4. **Run Application**: Start local server with `kivi serve` and open [http://127.0.0.1:8000](http://127.0.0.1:8000).
5. **Run Evaluation**: Execute canonical deterministic evaluation with `kivi evaluate --mode deterministic`.
6. **Inspect State**: Verify database counts with `kivi inspect`.

---

## AI Use and Attribution

AI tools supported research, implementation, debugging, and review under the direction of Basavaraj A. Naduvinamani. Product direction, architecture, empirical testing, validation, and final submission decisions were conducted and approved by Basavaraj A. Naduvinamani.
