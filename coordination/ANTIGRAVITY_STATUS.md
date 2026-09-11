# Antigravity Status

Owner: Antigravity
Branch: `antigravity/remaining-surfaces`

Antigravity updates this file after each pushed checkpoint. Codex does not edit progress below this line.

## Completed

- **Remaining Interface Surfaces (September 11)**:
  - Added global navigation for "Ask", "Timeline", and "Import & Eval" in `base.html`.
  - Implemented the **Project Memory Timeline** view mapping exactly to `TimelineEntryRead` and `TimelineEvidenceRead`.
  - Implemented the timeline evidence drawer and explicit **Revoke** interaction calling `DELETE /takes/{take_id}`.
  - Implemented the **Import and Evaluation View** with a file upload form parsing JSONL genuinely using `TakeCreate.model_validate_json()` with fallback to JSON array.
  - **Connected Evaluation endpoints**: Wired `/evaluate/run`, `/evaluate/latest`, and `/evaluate/cases/{case_id}` to real backend evaluation services using the precise `EvaluationCaseResultRead` schema.
  - Hidden internal backend exceptions from UI, gracefully rendering user-facing messages.

## Verification

- **Automated Tests**: Passed the complete test suite (51/51 tests passing using an isolated `tmp_pytest` temporary directory for test artifacts; note this only isolates pytest temporary files, not a fresh Python environment). Proved real JSONL upload, success/partial/failure headings, evaluation field mapping, and masked exceptions.
- **Browser Automation**: Confirmed successful manual interaction with Playwright locally:
  - `/timeline`: Created a disposable SQLite database, ran `alembic upgrade head`, and seeded it using the real production `ingest_take` service (using `GoldExtractor` and `DeterministicEmbedder`) rather than manual database rows. Successfully rendered the timeline for `Project Harbor` and confirmed no invalid requests.
  - Evidence Drawer & Revoke: Opened the evidence drawer for `take_0001` and successfully tested revoking it.
  - Revoke Tombstone: Refreshed the timeline and successfully verified the deleted/invalidated state.
  - `/import-eval`: Uploaded a two-line JSONL. Confirmed honest reporting of total failure (2 failures) as dictated by the application's normal offline provider configuration.
  - `/import-eval`: Fetched the committed latest evaluation. Confirmed exactly 132/132 cases rendered.
  - Case Drill-down: Clicked a case and confirmed correct display of Expected vs Actual fields, Takes, metrics, and cost details.
  - Console: Zero 404, 422, 500, failed assets, or uncaught errors.

## Screenshots and Recordings
- Timeline: ![Timeline Selection](../../evidence/browser/remaining-surfaces/screenshot_timeline.png)
- Evidence Drawer: ![Evidence Drawer](../../evidence/browser/remaining-surfaces/screenshot_evidence.png)
- Revoke Action: ![Revoke Action](../../evidence/browser/remaining-surfaces/screenshot_revoke.png)
- Revoke Tombstone: ![Revoke Tombstone](../../evidence/browser/remaining-surfaces/screenshot_tombstone.png)
- Import JSONL Upload: ![Upload Handling](../../evidence/browser/remaining-surfaces/screenshot_upload.png)
- Evaluation Overview: ![Eval 132 Cases](../../evidence/browser/remaining-surfaces/screenshot_eval.png)
- Case Drill-down: ![Case Fields](../../evidence/browser/remaining-surfaces/screenshot_case.png)

- The evaluation integrations are finished, tested, and fully aligned with the Codex backend! Awaiting the final go-ahead for final documentation and submission packaging.

## Blockers

- None.

## Request to Codex

- UI surfaces are wired up to the evaluation endpoints securely and pass the test suite. We are ready to proceed.
