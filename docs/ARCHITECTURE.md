# Kivi Architecture

Kivi implements project-scoped semantic memory tracking. The system enforces logical correctness, temporal validity, and evidence linkage independently of any downstream language model.

## Core Components

1. **Take Ingestion & Pipeline**: Source texts (Takes) enter the system and are converted to vectors for future indexing.
2. **Extraction Engine**: Extracts facts, categorizing them as EPISODE, DECISION, PREFERENCE, or CLAIM memory types.
3. **Memory Lifecycle**: Memories exist with epistemic and lifecycle statuses. Modifying an active memory produces a `SUPERSEDED` original and an `ACTIVE` updated memory. 
4. **Retrieval**: Combines deterministic rules (project scopes, deletion checks, required evidence limits) with continuous-space retrieval using embedded vector similarity.
5. **Grounded Answerer**: Uses the extracted deterministic memory items and produces claims explicitly tied to source Takes, avoiding un-cited hallucinatory assertions.

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite, SQLAlchemy, Alembic (for migrations), `sqlite-vec` (for vector embeddings, optionally)
- **Frontend**: HTMX, Jinja2 Templates
- **Evaluation**: Pytest, integrated deterministic test suites
