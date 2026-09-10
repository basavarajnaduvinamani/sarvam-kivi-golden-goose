# Backend and Frontend Integration Contract

Contract version: `1.1`  
Source implementation: `backend/kivi/schemas.py`  
Frozen for the September 11 remaining interface surfaces

## Ask request

`POST /ask`

```json
{
  "project_id": "project-harbor",
  "question": "When is the Project Harbor release?"
}
```

`project_id` may be `null`. When explicit project scope cannot be resolved, the backend returns `NEEDS_CLARIFICATION` without generating an answer.

## Ask response

```json
{
  "query_id": "qry_example",
  "status": "ANSWERED",
  "answer": "Project Harbor's release is Thursday at 4 PM.",
  "project_id": "project-harbor",
  "claims": [
    {
      "claim_text": "Project Harbor's release is Thursday at 4 PM.",
      "memory_ids": ["mem_example"],
      "supporting_take_ids": ["take_0001"]
    }
  ],
  "supporting_take_ids": ["take_0001"],
  "decision_reason": "Answer generated from the locked, project-scoped evidence package.",
  "retrieval_latency_ms": 4,
  "end_to_end_latency_ms": 62,
  "model_name": "configured-model",
  "input_tokens": 120,
  "output_tokens": 24,
  "estimated_cost_usd": null
}
```

## Typed statuses

- `ANSWERED`: Render answer and claim-level citations.
- `NO_EVIDENCE`: Render a plain abstention; do not render invented content.
- `NEEDS_CLARIFICATION`: Ask the user to select or state the project.
- `CONFLICTING_EVIDENCE`: Render the conflicting claims and their separate citations; do not choose a winner.
- `SERVICE_ERROR`: Render an actionable retry/configuration state distinct from missing evidence.

`answer` is nullable. `claims` and `supporting_take_ids` are always arrays. Token and cost fields are nullable when the provider does not supply enough information.

## Evidence navigation

Each `supporting_take_ids` value opens:

`GET /takes/{take_id}`

Relevant response fields:

```json
{
  "id": "take_0001",
  "project_id": "project-harbor",
  "raw_asr": "...",
  "formatted_text": "...",
  "source_application": "ChatGPT",
  "event_ts": "2026-09-10T09:30:00Z",
  "ingested_ts": "2026-09-10T09:31:00Z",
  "source_metadata": {},
  "embedding_model": "text-embedding-3-small",
  "is_deleted": false,
  "tombstoned_at": null
}
```

## Project selection

`GET /projects` returns an array:

```json
[
  {
    "id": "project-harbor",
    "name": "Project Harbor",
    "aliases": ["Harbor"],
    "created_at": "2026-09-10T09:00:00Z",
    "updated_at": "2026-09-10T09:00:00Z"
  }
]
```

## Memory inspection

`GET /memories?project_id=project-harbor&lifecycle_status=ACTIVE`

Each memory exposes separate `epistemic_status` and `lifecycle_status` plus its evidence list. The UI must not merge these two concepts.

## Project timeline

`GET /projects/{project_id}/timeline`

The response contains `project` and chronologically ordered `entries`. Each entry exposes `memory_id`, memory type, subject, predicate, value, separate epistemic and lifecycle states, validity timestamps, creation time, forward and reverse supersession IDs, and evidence summaries. Evidence summaries contain Take ID, source application, event time, span, role, required flag, and deletion flag. Timeline history includes superseded and invalidated memories; the UI must not present them as current facts.

## Import view

`POST /takes/import` accepts a JSON array conforming to `TakeCreate`. The existing `CorpusImportResult` returns `total`, `ingested`, `memories_created`, `unscoped`, `failed`, and `errors`. Each error contains `take_id`, `error_type`, and `detail`. The frontend owns file selection and JSONL-to-array parsing; the backend remains the authority for validation and ingestion.

## Grounded briefing

`POST /briefings`

```json
{
  "project_id": "project-harbor",
  "focus": "Provide the current project state and unresolved items."
}
```

The response is the same typed, claim-cited `AskResponse` used by `/ask`.

## Evaluation

`POST /evaluate/run` accepts `{ "mode": "deterministic" }` or `{ "mode": "candidate" }`. `GET /evaluate/latest` returns the latest complete run, and `GET /evaluate/cases/{case_id}` returns one case from that run.

An evaluation run contains `run_id`, `mode`, timestamps, corpus and case counts, aggregate `metrics`, complete case results, and repository-relative JSON and Markdown artifact paths. Each case contains identity and category, project scope, question, expected and actual typed status, pass/fail and reasons, structured expected/actual data, implicated memory and Take IDs, duration, model usage, and cost. Metrics contain overall/category pass rates, task-specific accuracy measures, all five hard-integrity violation counts, p50/p95 timing, database growth, tokens, and estimated cost.

## Compatibility rules

1. Frontend code must not infer meaning from HTTP success alone; it must branch on `status`.
2. Citations must come from `claims[].supporting_take_ids`, not from parsing answer text.
3. `CONFLICTING_EVIDENCE` may contain an answer explanation and multiple claims.
4. Deleted takes may remain inspectable as tombstone metadata, but purged content fields will be `null`.
5. No frontend fallback may transform `NO_EVIDENCE` or `SERVICE_ERROR` into an answer.
6. Field-name or enum changes require a contract-version update and coordinated tests.
