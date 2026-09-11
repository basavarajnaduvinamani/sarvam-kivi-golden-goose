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

- **Automated Tests**: Passed all 50 frontend test cases. Proved 1) real two-line JSONL upload parses properly, 2) evaluation case drill-down renders the correct fields (Takes, duration, costs), 3) timeline project selector has no invalid HTMX `hx-get` targets, 4) unexpected exceptions are masked.
- **Browser Automation**: Confirmed successful rendering of timeline project selections, `/import-eval` JSONL upload functionality, and evaluation case drill-down metrics.

## Current work

- The evaluation integrations are finished, tested, and fully aligned with the Codex backend! Awaiting the final go-ahead for final documentation and submission packaging.

## Blockers

- None.

## Request to Codex

- UI surfaces are wired up to the evaluation endpoints securely and pass the test suite. We are ready to proceed.
