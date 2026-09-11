# Codex Status

Last updated: September 11, 2026

Branch: `codex/functional-product-core`

Contract version: `1.2`

Milestone state: `BACKEND_CHECKPOINT_READY`

## Completed

- Preserved the completed evaluation, corpus, lifecycle, provenance, deletion, timeline, and briefing implementation from `main`.
- Froze integration contract version 1.2 for explicit user corrections and unscoped-take confirmation.
- Added a user-confirmed correction service that creates a new immutable Take and correction memory, preserves the original, records Take-ID evidence, and closes the superseded memory's validity interval.
- Added explicit unscoped-take project confirmation without semantic scope inference.
- Reused the existing extraction pipeline after project confirmation rather than creating memory through a parallel path.
- Added API routes for listing unscoped takes, confirming project scope, and correcting active memories.
- Added regression coverage for correction provenance, supersession, temporal validity, scoped processing, and reassignment rejection.

## Verification

- Focused contract and vertical-slice tests: 17 passed, 0 failed.
- Complete pytest suite: 54 passed, 0 failed, 0 skipped, 2 dependency deprecation warnings.
- Python compilation: passed.
- `git diff --check`: passed.
- Part One files: unchanged.

## Request to Antigravity

After this branch is reviewed and merged:

1. Read integration contract version 1.2 before editing frontend code.
2. Add an unscoped inbox using `GET /takes?unscoped_only=true` and explicit `POST /takes/{take_id}/scope` confirmation.
3. Add correction controls only to active timeline memories using `POST /memories/{memory_id}/correct`.
4. Refresh the timeline after correction and visibly preserve the superseded memory beside the new correction and its Take-ID evidence.
5. Add a grounded briefing interaction using the existing `POST /briefings` contract and the same five typed result states as Ask.
6. Do not infer or preselect project scope from semantic similarity.
7. Add frontend tests and browser evidence for all three interactions, then stop for Codex review.

## Stop Boundary

The critical Milestone 1 backend checkpoint is complete. No frontend implementation, visual redesign, candidate-provider run, documentation, or submission packaging begins until this checkpoint is reviewed and merged.
