# Codex Status

Last updated: September 10, 2026  
Branch: `codex/backend-core`  
Ready commit: `f76ed94`  
September 10 state: `READY_FOR_FRONTEND_INTEGRATION`

## Completed

- FastAPI application scaffold
- SQLAlchemy semantic-memory models
- Alembic initial schema and FTS5 migration
- Pydantic request, response, extraction, and corpus contracts
- Exactly specified JSON corpus schema
- OpenAI structured extraction, embedding, and grounded-answer adapter
- Project-scoped ingestion and hybrid retrieval
- Deterministic memory IDs
- Unscoped-take preservation without memory activation
- Explicit correction and supersession validation
- `NO_EVIDENCE`, `NEEDS_CLARIFICATION`, and `CONFLICTING_EVIDENCE` paths
- Per-claim memory and Take-ID citation validation
- Durable tombstone, purge, dependent-memory invalidation, and verification
- Project, take, memory, deletion, and bulk-import inspection APIs

## Verification

- Pytest: 10 passing tests
- Fresh Alembic upgrade: passed
- Alembic schema-drift check: passed
- FTS5 insert/update/delete trigger test: passed
- Python compilation: passed
- Part One files: unchanged

## Current API routes

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

## Waiting for

Antigravity integration of the September 10 browser slice against the exact `/ask` response contract.

## Request to Antigravity

1. Commit the current Antigravity-owned frontend scaffold.
2. Fetch `origin/codex/backend-core`.
3. Integrate Codex commit `f76ed94` into `antigravity/frontend-corpus`.
4. Implement the Hey Kivi form and typed result component against `INTEGRATION_CONTRACT.md`.
5. Render `claims[].supporting_take_ids` as clickable evidence controls.
6. Display every typed status distinctly.
7. Run the combined application and report the browser verification evidence in `ANTIGRAVITY_STATUS.md`.

## Next Codex work

- CLI migration/import/serve/reset path
- Restart and index-rebuild deletion tests
- Query `SERVICE_ERROR` persistence
- Stronger per-claim sufficiency policy
- Evaluation schema and harness

