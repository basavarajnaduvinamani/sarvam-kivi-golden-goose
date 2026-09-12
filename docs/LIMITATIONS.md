# Kivi System Limitations

This document provides a transparent, technically specific accounting of the architectural boundaries, operational constraints, and evaluation limits of the Kivi semantic memory demonstration.

---

## Architectural & Scope Boundaries

### 1. Single-User / Single-Tenant Identity
- **Scope Model**: Kivi enforces strict project-level isolation, but operates under a single-tenant identity model.
- **Access Control**: There is no multi-user authentication, tenant namespace partitioning, or role-based access control (RBAC). The architecture assumes a single knowledge worker managing their own projects, notes, and dictations on a single machine.
- **Concurrent Collaboration**: If multiple individuals submit dictations to the same project space simultaneously, conflicting statements will trigger `CONFLICTING_EVIDENCE` abstentions unless explicit supersession metadata is supplied.

### 2. Synchronous Execution Pipeline
- **Request Lifecycle**: Ingestion, vector embedding generation, relational persistence, candidate scoring, and query generation execute synchronously within FastAPI request cycles.
- **Worker Saturation**: The system lacks an asynchronous job queue (such as Celery, Bull, or RabbitMQ) or distributed worker pool. Ingesting large batches of unindexed audio/text or running concurrent multi-second LLM inferences can saturate the server process and result in elevated response latency or client timeouts.
- **Corpus Scale Target**: Designed and tuned for small-to-medium personal corpora (~500 to 1,000 takes). Ingesting tens of thousands of records requires adding asynchronous batching and queue management.

### 3. In-Process Vector Search & SQLite Limits
- **Storage Subsystem**: All relational data, full-text indexes, and embedding vectors reside in a local SQLite database (`var/kivi.db` or `var/evaluation.db`).
- **Vector Indexing**: Dense embeddings are stored as raw binary BLOBs (`LargeBinary`) in SQLite. Cosine similarity is computed via in-process NumPy matrix dot products over active candidate takes.
- **Scalability Ceiling**: While in-process NumPy scoring yields excellent sub-5ms retrieval latency on 500 takes, this linear scan approach ($O(N)$) does not scale to hundreds of thousands of vectors. A production deployment at scale would require an approximate nearest neighbor (ANN) index (e.g., HNSW via pgvector, Qdrant, or Milvus).

### 4. Application Context Ingestion
- **Metadata Reporting**: Kivi tracks application context (`source_application`, `source_metadata`) solely through fields supplied by the dictation client or replay corpus.
- **No Native OS Hooks**: The current repository does not include low-level OS accessibility listeners, window focus monitors (e.g., Windows UI Automation or macOS Accessibility APIs), or system tray global hotkeys. The caller is responsible for supplying the active application name with each utterance.

### 5. Multilingual & Dialectal Nuance
- **Token Preservation**: Indic code-switching (e.g., Kannada, Hindi-English) is preserved verbatim in SQLite text fields and indexed using SQLite FTS5 with the `unicode61` tokenizer.
- **Semantic Extraction Variance**: In candidate evaluation mode, the quality of entity extraction and relationship discovery on code-switched speech depends entirely on the external foundation model's multilingual tokenizer and training distribution. Colloquial code-switching without explicit project nouns may fail extraction or require user-directed scoping in the Inbox.

---

## Evaluation Constraints & Execution Status

### 6. Deterministic Suite vs. Live Foundation Models
- **Canonical Deterministic Results**: The canonical 132/132 evaluation run (`evalrun_3bb3ebb25f16`) executed offline with `GoldExtractor`, `DeterministicEmbedder`, and `DeterministicAnswerer`.
- **Scope of Deterministic Verification**: Deterministic evaluation verifies structural invariants: evidence link completeness, project isolation, required evidence gating, deletion integrity after FTS rebuilds, temporal supersession state machines, and epistemic abstention rules.
- **No Natural Language Simulation**: Deterministic evaluation does **not** evaluate natural language fluency, stylistic coherence, open-ended paraphrasing, or probabilistic ambiguity handling of live foundation models.

### 7. Candidate Evaluation Mode: Not Yet Executed
- **Execution Status**: Candidate mode (`kivi evaluate --mode candidate`) connects live foundation models (the configured OpenAI model and embedding model) to the pipeline. **Candidate mode has not yet been executed in this repository submission.**
- **Prerequisites**: Running candidate mode requires setting `OPENAI_API_KEY` in `.env` and supplying sufficient token budget.
- **Unverified Candidate Metrics**: Live answer quality, token usage costs, and real-world prompt latency under candidate provider mode remain unmeasured in the committed evaluation reports and are deferred to external reviewer execution.

---

## Operational & Deployment Boundaries

### 8. Local Deployment Focus
- **Target Environment**: The application is designed and tested as a local workstation web service (Python 3.11+, SQLite, Uvicorn).
- **Enterprise Operations**: Out of the box, the codebase does not include multi-region failover, container orchestration manifests (Kubernetes Helm charts), automated backup snapshots, or remote cloud database configurations.

### 9. Financial Cost of Live Operations
- **Deterministic Operations**: All deterministic evaluations, corpus validation, database migrations, and local UI workflows incur zero API costs ($0.00).
- **Provider Costs**: Operating candidate mode or using live OpenAI providers for extraction and answering incurs token costs proportional to corpus volume and query frequency. Reviewers should monitor API spend when running candidate evaluations.
