# Kivi Golden Goose Part Two - Delivery Specification

Status: Approved implementation contract  
Deadline: September 12, 2026, end of day (Asia/Calcutta)  
Primary review method: Completely local web application with a documented model credential

## 1. Purpose

Part Two will deliver one working end-to-end demonstration of project-scoped semantic memory for Kivi. The product will recover the current state of a project from intentional dictations across applications while preserving corrections, decision status, provenance, project isolation, abstention, and deletion.

The completed Part One positioning statement and vision document are frozen inputs. They must not be rewritten during Part Two.

## 2. Governing principles

1. Product usefulness comes before breadth.
2. Ordinary dictation remains the capture surface; semantic memory principally changes Hey Kivi.
3. Project boundaries are authorization boundaries, not similarity hints.
4. Similarity retrieves candidates but never authorizes a claim.
5. Every answer claim must be supported by currently valid source evidence.
6. Proposed, rejected, quoted, hypothetical, conditional, and approved statements must remain distinguishable.
7. Corrections preserve history while changing the active state.
8. Deletion must affect every query path before success is reported.
9. Failures, conflicts, abstentions, latency, storage, model usage, and cost must remain inspectable.
10. Reviewer reproducibility is a product requirement.

## 3. Product scope

The demonstration will support five connected capabilities:

1. Recover the latest project state through Hey Kivi.
2. Explain what changed through a temporal memory timeline.
3. Distinguish approved, proposed, rejected, conditional, and unresolved information.
4. Produce a grounded project briefing or handoff from valid evidence only.
5. Inspect, correct, and revoke memory through a normal-user interface.

The demonstration will replay transcript and application-context events. Speech recognition and production Kivi integration are out of scope.

## 4. Technology stack

- Runtime: Python 3.12
- Web backend: FastAPI and Uvicorn
- Validation: Pydantic
- Persistence: SQLite
- ORM and migrations: SQLAlchemy 2 and Alembic
- Keyword retrieval: SQLite FTS5
- Semantic retrieval: embedding vectors stored in SQLite, with cosine similarity computed in Python using NumPy
- Interface: Jinja2, vendored HTMX, and local CSS
- Model integration: provider adapter, initially using the OpenAI Responses API
- Default extraction and grounded-answer model: configurable through environment variables
- Default embedding model: `text-embedding-3-small`, configurable through environment variables
- Tests: Pytest
- Evaluation: standalone Python harness producing JSON and Markdown reports

The application must require no Node build, CDN resource, Docker service, hosted database, or undocumented dashboard configuration.

## 5. System boundaries

The model may propose structured memories and answer wording. Deterministic application policy controls project scope, lifecycle transitions, evidence validity, citation validity, deletion, and response status.

The system must not infer a project boundary from semantic similarity alone. If explicit metadata and conversational context cannot resolve the project safely, the response must be `NEEDS_CLARIFICATION`.

## 6. Core data model

### 6.1 Projects

- Stable project ID
- Display name
- Optional aliases
- Created timestamp
- Updated timestamp

### 6.2 Takes

- Stable Take ID
- Project ID, nullable until scope is resolved
- Raw ASR
- LLM-formatted output
- Source application
- Event timestamp
- Ingestion timestamp
- Ordinary source metadata as JSON
- Embedding vector and embedding-model identifier
- Deletion state and tombstone timestamp

Takes are immutable evidence until deletion. Corrections create new takes and memories rather than overwriting source history.

### 6.3 Memories

- Stable memory ID
- Project ID
- Memory type
- Subject
- Predicate
- Object/value
- Epistemic status
- Lifecycle status
- Valid-from and valid-to timestamps
- Confidence
- Extraction method and model identifier
- Prompt/schema version
- Superseded-memory relationship
- Created and updated timestamps

Epistemic status:

- `PROPOSED`
- `APPROVED`
- `REJECTED`
- `CONDITIONAL`
- `UNRESOLVED`

Lifecycle status:

- `ACTIVE`
- `SUPERSEDED`
- `INVALIDATED`
- `TOMBSTONED`

Memory types will be limited to those required by the product: decision, constraint, commitment, correction, rejected proposal, condition, unresolved question, episode, and durable preference.

### 6.4 Memory evidence

- Memory ID
- Take ID
- Supporting span start and end
- Evidence role
- Sufficiency contribution

Every activated memory requires evidence. Every answer claim requires a currently sufficient subset of valid evidence.

### 6.5 Tombstones

- Take ID
- Created timestamp
- Logical deletion status
- Purge status
- Purged timestamp
- Verification timestamp
- Failure detail, when applicable

### 6.6 Query runs and claims

Each query run will preserve:

- Query ID
- Project scope
- Original question
- Typed response status
- Answer text
- Candidate and selected memory IDs
- Per-claim supporting Take IDs
- Decision reason
- Retrieval and end-to-end latency
- Model and prompt versions
- Input/output tokens
- Estimated cost
- Created timestamp

## 7. Corpus import contract

The repository will commit exactly 500 transcript-like JSONL records and the schema used to validate them.

Required fields:

- `take_id`
- `raw_asr`
- `formatted_text`
- `source_application`
- `event_ts`
- `metadata`

`metadata` may contain an explicit project ID or other ordinary log context. The importer must also accept the reviewers' equivalent field mapping without requiring source-code changes.

The corpus package will contain:

- Final 500-record JSONL corpus
- JSON Schema
- Fixed-seed deterministic generator
- Generation manifest and category counts
- Gold project, entity, status, and temporal labels
- Evaluation cases stored separately from implementation logic

Corpus coverage must include multiple applications, similar projects, distributed evidence, corrections, rejected and quoted proposals, conditions, negations, ambiguity, multilingual code-switching, protected identifiers, deletion sentinels, unsupported questions, and service-error fixtures.

## 8. Ingestion and memory-creation pipeline

1. Validate every input record against the import schema.
2. Persist the immutable take.
3. Resolve project scope from explicit evidence only.
4. Create and store the take embedding.
5. Ask the extraction model for structured candidate memories, statuses, entities, time information, and exact evidence spans.
6. Validate the model output against a versioned schema.
7. Apply deterministic activation, rejection, correction, and conflict policies.
8. Persist memories and evidence links transactionally.
9. Record model identifier, prompt/schema version, tokens, latency, cost, and decision reason.
10. Preserve ignored or rejected extraction decisions for inspection.

Invalid model output must not create a partial memory. It must produce an inspectable processing failure.

## 9. Retrieval and answer pipeline

1. Resolve explicit project scope; otherwise return `NEEDS_CLARIFICATION`.
2. Hard-filter to the selected project before any ranking.
3. Exclude tombstoned takes and invalidated, tombstoned, or historically superseded memories from current-state answering.
4. Retrieve candidates through embeddings and FTS5.
5. Resolve entity, predicate, epistemic status, lifecycle status, temporal validity, and supersession.
6. Detect unresolved contradictory evidence.
7. Apply a per-claim evidence-sufficiency gate.
8. Return `NO_EVIDENCE` when valid evidence cannot support the requested claim.
9. Return `CONFLICTING_EVIDENCE` when incompatible active claims remain unresolved.
10. Generate answer wording from the locked evidence package only.
11. Reject hallucinated, missing, cross-project, deleted, or otherwise invalid citations.
12. Store the complete query trace and measurements.

Typed response statuses:

- `ANSWERED`
- `NO_EVIDENCE`
- `NEEDS_CLARIFICATION`
- `CONFLICTING_EVIDENCE`
- `SERVICE_ERROR`

## 10. Correction and supersession

A correction creates a new memory version. The prior memory becomes `SUPERSEDED` but remains inspectable as history.

Automatic supersession requires compatible project, subject/entity, predicate, and temporal relationship. Semantic similarity alone is insufficient. When a safe correction relationship cannot be established, both memories remain visible and the system returns `CONFLICTING_EVIDENCE` where appropriate.

## 11. Two-phase deletion

Phase one occurs transactionally before logical deletion success is displayed:

1. Create a durable tombstone.
2. Mark the source take deleted.
3. Exclude the take from every read and retrieval path.
4. Invalidate every dependent memory.
5. Invalidate derived answers, indexes, and caches.
6. Re-derive an affected memory only when the remaining evidence independently supports the complete claim.
7. Commit the transaction.

Phase two purges removable content:

- Raw ASR
- Formatted output
- Embedding data
- Cached content derived from the take

The tombstone and non-content audit metadata remain so that restarts and rebuilds cannot resurrect deleted evidence. Purge and verification status must be inspectable.

Deletion acceptance tests must cover immediate queries, fresh sessions, application restart, database reopening, and index rebuild.

## 12. API contract

Minimum API surface:

- `GET /health`
- `GET /projects`
- `POST /projects`
- `GET /takes`
- `POST /takes`
- `POST /takes/import`
- `GET /takes/{take_id}`
- `DELETE /takes/{take_id}`
- `GET /deletions/{take_id}`
- `GET /memories`
- `GET /memories/{memory_id}`
- `POST /ask`
- `POST /briefings`
- `POST /evaluate/run`
- `GET /evaluate/latest`

The `/ask` response contract contains:

- Status
- Answer
- Resolved project ID
- Claims
- Per-claim memory IDs and supporting Take IDs
- Decision reason
- Retrieval latency
- End-to-end latency
- Model usage and estimated cost

Shared request and response schemas must be frozen before frontend and backend implementation proceed in parallel.

## 13. User interface

The local web application will contain four connected surfaces:

1. Hey Kivi question and grounded-briefing surface
2. Evidence drawer showing original ASR, formatted output, application, timestamp, span, and Take ID
3. Project memory timeline showing epistemic and lifecycle states
4. Import and evaluation view showing progress, failures, metrics, and inspection links

The interface must visibly distinguish answers, insufficient evidence, required clarification, conflicting evidence, and service failures. It must never silently close or use one generic error presentation for semantically different states.

## 14. Evaluation specification

The committed evaluation will contain 120 to 150 deterministic cases, with 120 as the minimum delivery target.

Coverage:

- Cross-project lexical leakage
- Cross-project semantic leakage
- Cross-application recovery within one project
- Distributed multi-take evidence
- Temporal correction and supersession
- Epistemic status
- Quoted, hypothetical, rejected, conditional, and negative statements
- Unsupported-answer abstention
- Ambiguous project scope
- Per-claim provenance
- Partial-evidence deletion
- Deletion before and after restart
- Index rebuild after deletion
- Service failure versus `NO_EVIDENCE`
- Indic code-switching and protected identifiers
- Preference precedence

Hard integrity targets for the submitted corpus:

- Zero observed cross-project leakage
- Zero deleted-memory resurrection
- Zero invalid citations
- Zero rejected proposals promoted to approved actions
- Zero fabricated answers where evidence is absent

Reported measurements:

- Answer correctness
- Abstention precision and recall
- Conflict-detection accuracy
- Project-scope accuracy
- Decision-status accuracy
- Temporal-correction accuracy
- Provenance coverage
- Deletion integrity
- Retrieval and end-to-end p50/p95 latency
- Database growth
- Model tokens and estimated cost

Every case preserves input, expected result, actual result, relevant memory state, retrieved evidence, reason, model metadata, timing, and pass/fail result. Failures remain visible in the generated JSON and Markdown reports.

## 15. Reviewer operations

`RUN.md` will begin by declaring the primary review method and will contain exact commands for:

1. Required runtime and versions
2. Environment-variable setup and `.env.example`
3. Dependency installation
4. Database creation and migration
5. Seed and corpus import
6. Application startup
7. URL to open
8. Primary interactions to try
9. Candidate evaluation
10. Importing another corpus
11. Inspecting evaluation results and memory state
12. Resetting the complete system

Representative command responsibilities will be exposed through a coherent Python CLI. Tests, application startup, corpus import, evaluation, inspection, and reset are distinct operations.

The final submitted commit must pass a clean-clone rehearsal without relying on uncommitted data, hidden local state, undeclared services, or undocumented manual intervention.

## 16. Repository layout

```text
backend/                  FastAPI application and domain services
alembic/                  Database migrations
frontend/                 Jinja templates, vendored HTMX, CSS, and browser assets
corpus/                   500-record corpus, schema, manifest, and generator
evaluation/               Cases, harness, metrics, and report generation
tests/                    Unit, integration, restart, and end-to-end tests
docs/                     Part One and supporting architecture documents
results/                  Committed JSON and Markdown evaluation results
README.md                 Product, architecture, use cases, limitations, results, AI use
RUN.md                    Exact reviewer path
.env.example              Declared non-secret configuration
```

## 17. Collaboration and ownership

### Codex ownership

- Architecture and shared contracts
- SQLAlchemy models and Alembic migrations
- Pydantic and JSON schemas
- Corpus schema and deterministic generator
- Ingestion and memory extraction
- Policy and lifecycle engine
- Retrieval and evidence sufficiency
- Correction, conflict, and deletion services
- FastAPI routes
- Backend and integration tests
- Evaluation harness and metrics
- Technical documentation and final integration

### Antigravity ownership

- Jinja2 and HTMX interface
- Interaction design and visual system
- Hey Kivi experience
- Evidence drawer and memory timeline
- Import and evaluation views
- Frontend/browser tests
- Corpus-generation execution and visual inspection
- Windows clean-clone rehearsal
- Reviewer-path verification

### User ownership

- Product and submission authority
- Completed Part One authorship
- Approval of consequential product changes
- Approval of personal attribution and AI-use wording
- Final merge and submission decision

Claude and DeepSeek may provide optional contradiction reviews. Their suggestions do not change this specification unless accepted through an explicit decision.

## 18. Git workflow

- `main`: reviewed integration only
- `codex/backend-core`: backend, evaluation, and integration work
- `antigravity/frontend-corpus`: frontend, corpus execution, and visual verification work

Each agent commits only files within its ownership unless an integration change is explicitly coordinated. Shared schema and API changes require an explicit contract update before implementation. Part One files remain unchanged.

## 19. Delivery schedule

### September 10

- Freeze this specification, schemas, and API contracts
- Scaffold application and migrations
- Complete one thin vertical slice: import take, create memory, ask question, display cited answer

### September 11

- Complete project isolation, lifecycle policy, correction, conflict, abstention, provenance, and deletion
- Complete the four interface surfaces
- Generate and commit the 500-record corpus
- Run backend and browser integration tests

### September 12 morning

- Complete at least 120 evaluation cases
- Generate JSON and Markdown results
- Resolve integrity failures
- Complete README, RUN.md, `.env.example`, limitations, and architecture documentation

### September 12 afternoon

- Perform fresh-clone rehearsal
- Import an independently shaped sample corpus
- Verify startup, inspection, Hey Kivi, deletion, restart, evaluation, and reset
- Eliminate hidden state and undocumented steps

### September 12 evening

- Freeze repository
- Confirm Part One remains unchanged
- Obtain user approval for attribution and AI-use wording
- Record exact final commit SHA
- Push and verify the remote repository

## 20. Definition of done

Part Two is complete only when:

1. A normal user can import data, ask Hey Kivi, inspect sources, understand memory state, correct information, and delete evidence through the working product.
2. Backend behavior comes from actual persisted state, retrieval, policy, and model decisions.
3. Exactly 500 committed corpus records import successfully.
4. At least 120 reproducible evaluation cases run through the complete pipeline.
5. Every answer claim has valid provenance.
6. Cross-project, rejected-proposal, unsupported-answer, and deletion integrity gates pass.
7. Restart and index-rebuild tests cannot resurrect deleted evidence.
8. Latency, storage, model usage, cost, and individual failures are inspectable.
9. A clean clone can be installed, migrated, seeded, started, operated, evaluated, inspected, and reset solely by following RUN.md.
10. README contains an accurate AI-use disclosure approved by the user.
11. The final remote commit matches the submitted SHA.

## 21. Change control

This document is the single implementation contract. A change is accepted only when it is documented with:

- The reason
- The affected requirement or invariant
- The contract, schema, test, and documentation impact
- The user decision when the change affects product scope, authorship, attribution, or AI-use disclosure

Silent changes to shared schemas, response statuses, corpus size, integrity requirements, or reviewer operations are prohibited.
