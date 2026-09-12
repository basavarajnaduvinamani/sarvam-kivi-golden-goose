# Browser Evidence Gallery

Representative screenshots of Kivi's working local interface. All images were captured from the running application served at `http://127.0.0.1:8000`.

For the complete reviewer experience, follow the step-by-step runbook in [RUN.md](../../RUN.md).

## Interface surfaces

| Surface | Screenshot | Description |
|---|---|---|
| Hey Kivi — answered query | ![Ask answered](light-ui/02_desktop_ask_answered.png) | A project-scoped question returns an `ANSWERED` response with claim-level citations and Take ID evidence chips. |
| Evidence drawer | ![Evidence drawer](light-ui/03_desktop_evidence_drawer.png) | Clicking a Take ID chip opens the evidence drawer showing raw ASR, formatted text, source application, and timestamp. |
| Grounded briefing | ![Briefing](light-ui/04_desktop_briefing.png) | A project briefing returns a grounded answer with supporting evidence and typed status. |
| Timeline — correction | ![Timeline correction](functional-product/screenshot_timeline_corrected.png) | The timeline shows a superseded memory alongside its active correction, preserving full audit history. |
| Inbox — scope assignment | ![Inbox scoping](functional-product/screenshot_inbox_selection.png) | An unscoped take awaits explicit user project assignment. No project is preselected. |
| Import and evaluation | ![Import and eval](light-ui/07_desktop_import_eval.png) | The import view accepts JSONL corpus files; the evaluation panel displays 132/132 deterministic results. |

## Additional evidence

| Flow | Screenshot | Description |
|---|---|---|
| Timeline — revoke evidence | ![Revoke](remaining-surfaces/screenshot_revoke.png) | The revoke action requires explicit confirmation before deleting a take. |
| Tombstone inspection | ![Tombstone](remaining-surfaces/screenshot_tombstone.png) | After deletion, the tombstone metadata remains inspectable with purge and verification status. |
| Evaluation case detail | ![Case detail](remaining-surfaces/screenshot_case.png) | Individual evaluation cases show expected status, actual status, and pass/fail with failure reasons. |
