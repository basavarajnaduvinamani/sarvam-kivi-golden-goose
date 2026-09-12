# Browser Evidence Gallery

Representative screenshots of Kivi's working local interface. All images were captured from the running application served at `http://127.0.0.1:8000`.

For the complete reviewer experience, follow the step-by-step runbook in [RUN.md](../../RUN.md).

## Interface surfaces

| Surface | Screenshot | Description |
|---|---|---|
| Hey Kivi — answered query | ![Ask answered](magicpath-ui/01_ask_answered.png) | A project-scoped question returns an answered response with claim-level citations and Take ID evidence chips. |
| Evidence drawer | ![Evidence drawer](magicpath-ui/02_evidence_drawer.png) | Clicking a Take ID chip opens the evidence drawer showing raw ASR, formatted text, source application, and timestamp. |
| Grounded briefing | ![Briefing](magicpath-ui/03_briefing.png) | A project briefing returns a grounded answer with supporting evidence. |
| Timeline — correction | ![Timeline correction](magicpath-ui/04_timeline_correction.png) | The timeline shows a superseded memory alongside its active correction, preserving full audit history. |
| Inbox — scope assignment | ![Inbox scoping](magicpath-ui/05_inbox_scope.png) | Unscoped takes await explicit user project assignment. No project is preselected. |
| Import and evaluation | ![Import and eval](magicpath-ui/06_import_eval.png) | The evaluation panel runs and displays deterministic test results. |

## Additional evidence

| Flow | Screenshot | Description |
|---|---|---|
| Evaluation case detail | ![Case detail](magicpath-ui/07_eval_case.png) | Individual evaluation cases show expected status, actual status, and pass/fail metrics. |
| Timeline — revoke evidence | ![Revoke](magicpath-ui/08_revoke.png) | The revoke action requires explicit confirmation before deleting a take. |
| Tombstone inspection | ![Tombstone](magicpath-ui/09_tombstone.png) | After deletion, the tombstone metadata remains inspectable with purge and verification status. |
