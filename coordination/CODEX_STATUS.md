# Codex Status

Last updated: September 10, 2026  
Branch: `codex/september-11-backend`  
Ready code commit: `8612872`  
September 11 state: `READY_FOR_INTEGRATION`

## Completed

- Added explicit required-evidence semantics to each memory-evidence link.
- Enforced complete per-claim citations across every required supporting Take ID.
- Excluded memories when any required take is missing or deleted.
- Added deterministic correction linking only when exactly one active subject/predicate match exists.
- Returned and persisted typed `SERVICE_ERROR` query runs for embedding, answer, and citation-validation failures.
- Kept private provider diagnostics internal while returning safe reviewer-visible error wording.
- Added a fixed-seed generator and committed exactly 500 transcript-like records, gold labels, a 20-project registry, and a hash manifest.
- Added reviewer CLI commands for serve, migrate, guarded reset, FTS rebuild, project import, corpus validation/import, and state inspection.
- Added an active-and-sufficient-evidence FTS rebuild policy.
- Proved tombstone persistence, content purge, dependent-memory invalidation, and exclusion after process restart and index rebuild.

## Verification

- Pytest: 19 passing tests.
- Deterministic corpus check: 500 records and all committed hashes match.
- Corpus CLI validation: 500 records accepted.
- Fresh Alembic upgrade through `d164b8a1c321`: passed.
- Alembic schema-drift check: no new operations detected.
- Reviewer CLI migrate, rebuild-index, and inspect commands: passed on a fresh SQLite database.
- Python compilation and `git diff --check`: passed.
- Part One files: unchanged.

## Request to Antigravity

1. Finish and push the current frontend corrective checkpoint from the Antigravity-owned branch.
2. Fetch `codex/september-11-backend` and review commit `8612872`.
3. Integrate the branch only after the frontend checkpoint is clean, then run the complete combined browser and CLI flow.
4. Verify that all five statuses still render correctly and that evidence controls tolerate the added `is_required` field.
5. Record the integrated commit and browser evidence in `coordination/ANTIGRAVITY_STATUS.md`.

## Next Codex work — September 12 only

- Build the deterministic adversarial evaluation harness and metrics report.
- Complete `RUN.md`, architecture, design-decision, and evaluation documentation.
- Perform clean-clone reviewer rehearsal and final submission audit.
- No September 12 work begins until the user resumes the next bounded milestone.
