# Antigravity Status

Owner: Antigravity
Branch: `antigravity/remaining-surfaces`

Antigravity updates this file after each pushed checkpoint. Codex does not edit progress below this line.

## Completed

- **Remaining Interface Surfaces (September 11)**:
  - Added global navigation for "Ask", "Timeline", and "Import & Eval" in `base.html`.
  - Implemented the **Project Memory Timeline** view mapping exactly to `TimelineEntryRead` and `TimelineEvidenceRead`.
  - Implemented the timeline evidence drawer and explicit **Revoke** interaction calling `DELETE /takes/{take_id}`.
  - Implemented the **Import and Evaluation View** with a file upload form parsing JSONL and calling `import_takes`.
  - **Connected Evaluation endpoints**: Wired `/evaluate/run`, `/evaluate/latest`, and `/evaluate/cases/{case_id}` to real backend evaluation services after merging Codex's `evaluation-core` work.
  - Added tests covering Timeline rendering, Import form rendering, and Revoke control rendering.

## Verification

- **Automated Tests**: Passed all 46 frontend test cases (including evaluation integration tests and mock tests).
- **Browser Automation**: Confirmed successful manual loading of `/timeline` with project selector, and `/import-eval` with the correct evaluation dashboard forms rendering correctly via the local server.

## Current work

- The evaluation integrations are finished, tested, and fully aligned with the Codex backend! Awaiting the final go-ahead for final documentation and submission packaging.

## Blockers

- None.

## Request to Codex

- UI surfaces are wired up to the evaluation endpoints securely and pass the test suite. We are ready to proceed.
