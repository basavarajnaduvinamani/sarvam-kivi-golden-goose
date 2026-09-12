# Kivi Hands-On Evidence Dossier

> Research notes, not submission prose. This document records observed product behaviour from the Windows alpha build and is intended to help the applicant form an independent Part One position.

## Test environment

- Platform: Windows
- Kivi build shown in Settings: `1.8.1-alpha.5`
- Primary test applications: Notepad and ChatGPT
- Interaction modes tested: ordinary dictation, Hey Kivi, History search/answers, Dictionary, Shortcuts, Styles, app-specific voices, privacy settings, orb lifecycle
- Typical successful processing time: approximately one second after releasing the dictation shortcut
- Ordinary dictation shortcut: Left Ctrl + Windows
- Hey Kivi shortcut: Left Ctrl + Space

## What the product demonstrably does

### Ordinary dictation

- Captures speech while the shortcut is held and inserts text after release.
- Does not stream text progressively during speech.
- Usually processes within roughly one second while online.
- Removes common filler words and spoken correction scaffolding.
- Converts spoken structure into paragraphs, lists, punctuation, times, and numbers.
- A complete insertion can be removed with one Ctrl+Z operation.
- Six seconds of silence did not prematurely submit a take.
- Pressing Esc during recording cancelled the take; nothing entered Notepad or History.

### Multilingual and code-switched speech

- Roman Hinglish was transcribed accurately while preserving mixed Hindi and English.
- Native-script mode produced Hindi in Devanagari while retaining some English technical terms.
- Manual Hindi corrected a Priya-name error but inconsistently transliterated English terminology.
- Kannada Native mode cleanly preserved Kannada script, English technical phrases, names, time, and a negative instruction.
- Translation through Hey Kivi preserved protected English entities and decision status.

### Application-specific voices

- Notepad and ChatGPT followed different voice groups and instructions in the same test.
- Notepad produced balanced prose and its own tag.
- ChatGPT produced Developer Structured output with Goal, Context, and Constraints and its own tag.
- Instructions did not leak across the two applications during that test.

### Hey Kivi

- Works reliably on selected text when the service is healthy.
- Can rewrite, shorten, translate, and accept conversational follow-ups.
- Follow-ups retained the previous generated answer as `last edit`.
- A generated answer can be copied and manually edited.
- User-edited text became authoritative context for the next follow-up.
- Selecting text is important: unselected visible screen content could not be read in repeated Windows tests.

### History and semantic retrieval

- History records takes with application provenance.
- Search results update while the query is typed.
- Pressing Enter can generate an answer with numbered supporting sources.
- Kivi correctly abstained when evidence was insufficient in one approval question.
- It correctly resolved a rescheduled meeting from an older record to a newer correction.
- It synthesized facts distributed across three takes and cited the appropriate sources.
- It correctly resolved a cross-app update and identified ChatGPT as the application containing the correction.
- It correctly distinguished a rejected quoted suggestion from the only approved action.
- Take details expose both `what Kivi wrote` and `what you said`.

### Windows lifecycle

- Closing the main window leaves the orb running intentionally.
- The orb is described in Settings as an `always-present surface`.
- The system-tray menu provides Open Kivi, Record, Hey Kivi, Language, Script, Microphone, Settings, and Exit.
- Tray Exit closes the orb and removes the Kivi process completely.
- A configured top/bottom orb position persisted through a full restart.
- Manually dragging the orb is distinct from changing its saved position setting.

## Strongest observed product qualities

1. **Very low interaction cost:** hold, speak, release, and receive formatted text quickly.
2. **Strong semantic cleanup:** fillers, corrections, uncertainty, negatives, and lists are often handled well.
3. **Indian-language code-switching:** Kannada and Roman Hinglish results were particularly strong.
4. **Application-aware output:** the same speech can be rendered differently for Notepad and ChatGPT.
5. **Inspectability:** History answers expose supporting takes and application labels.
6. **Safe cancellation:** Esc discarded an active take without inserting or storing it.
7. **Grounded decision status in successful cases:** rejected, proposed, uncertain, approved, and cancelled statements were often distinguished correctly.

## Reliability limitations observed

### Proper nouns and technical identifiers

- `authservice.ts` lost `.ts`.
- `getUser` became `gotUser`.
- `Aaditya` often became `Aditya` without an explicit same-utterance spelling or a working Dictionary application.
- `Priya` became `क्रिया` in Auto-detect + Native Hindi.
- `Project Banyan` became `Project Panyan`.
- `Maya Rao` became `Mayarao`.
- `Project Cedar` repeatedly became `Project Sedar`.
- `Project Zinnia` became `Project Zina`.
- `memory test` became `memory trust`.

### Semantic drift

- `customer note` became `customer role` once.
- `requests` became `requires` once.
- `approved launch schedule` became `approval launch schedule`.
- A History summary changed `Priya will record` into `Priya should record`.
- A follow-up initially attached Maya's approval to API readiness rather than specifically to deployment.

### Retrieval contamination

- A Project Cedar customer-brief request returned unrelated generic launch-review facts.
- Even when explicitly told to use only Project Sedar takes, the answer imported Aditya and Priya from an unrelated meeting instead of Maya Rao and Priya Sharma.
- Relevant sources may appear lower in supporting results while the generated answer uses a higher-ranked irrelevant source.
- Supporting-take panels often include many irrelevant records below the correct evidence.

### Raw speech versus final written text

- Supporting takes sometimes expose a rawer transcript than the final inserted output.
- Corrected-away details such as an obsolete time or date may remain visible in the source transcript.
- Retrieval therefore needs to understand corrections inside a take, not merely index every spoken fragment equally.

## High-severity trust and privacy finding

### Deleted history remained retrievable

A unique fictional record containing `blue 79` was deleted through the History interface.

Observed sequence:

1. Kivi asked for confirmation before deletion.
2. The take disappeared from the normal History list.
3. An identical question still returned the deleted fact.
4. A different fresh question abstained but displayed the deleted record as the first supporting take.
5. After fully exiting Kivi and restarting it, another fresh question confidently returned `blue 79` and cited the deleted record.

Conclusion limited to observation: visible deletion did not remove or exclude the record from semantic retrieval, even across a full restart.

## Settings and feature defects

### Dictionary

- The Dictionary accepts a term and an optional usage note.
- An Aaditya correction worked immediately after creation.
- The entry remained visibly saved after restart.
- Its correction was not applied after the restart.

### Phrase shortcuts

- The Shortcuts page provides `you say` and `Kivi writes` fields and supports up to 500 active shortcuts.
- A saved shortcut remained visibly active.
- Exact and inline spoken triggers did not expand, including after removing contaminating style instructions.

### Paste Last

- Settings advertise Ctrl+Shift+V as `paste last`.
- A controlled sentinel test showed that Notepad received an ordinary clipboard paste instead.
- The orb did not react and no Kivi last take was inserted.

### Style and instruction persistence

- Style execution worked when settings successfully saved.
- Save-button visibility was intermittently inconsistent.
- ChatGPT could remain on Structured after attempts to switch back to Clear.
- Cleared ChatGPT instructions could reappear after reopening the settings screen.
- Notepad could visually select Polished but later reopen on Balanced.
- This appears to involve dirty-state detection or synchronization between app overrides and shared voice-group state.

### Inactivity timeout

- The General setting was configured to two minutes.
- The main window, orb, panels, and visible session state remained unchanged beyond three minutes.
- No countdown or explanation appeared.
- The setting may govern an invisible internal state, but it had no observable effect in the test.

### Screen context

- Screen context was enabled in Data & Privacy.
- Kivi could identify Notepad as the active application but could not read manually typed, visible, unselected text.
- Repeated attempts either produced `I can't see any code...` or listened and silently closed.
- Selected-text Hey Kivi continued to work.
- System Settings exposed microphone controls but no screen-capture permission or diagnostic status.

### UI issues

- Generated History answers could not be copied, although individual takes have copy icons.
- History citation `[1]` did not navigate to its supporting take.
- Answer-panel scrollbars visually crowd or overlap the Close label.
- Markdown markers such as `**...**` and `###` sometimes appear literally.
- Double-clicking an orb answer to edit first triggers the single-click copy action, overwriting existing clipboard contents.
- The edit view has no explicit Save button; starting Follow up implicitly commits the edit.
- Hey Kivi occasionally listened and silently closed without producing a question or answer, then self-recovered later.

## Connectivity and data behaviour

- Basic dictation failed while offline.
- The orb displayed a generic `something failed` message.
- Reconnecting did not resume or queue the failed take.
- The failed take did not enter History.
- Once connectivity returned, dictation recovered immediately without restarting Kivi.
- This rules out describing the tested Windows build as fully offline.
- It does not independently establish the precise server-side architecture.

Current privacy settings observed:

- Screen context: on during the audit
- Keep memory on this device only: off
- Retry failed dictations: on
- Don't use dictation data to train AI models: off
- Apply zero data retention policy: off
- UI statement: audio is processed in real time and never stored on Kivi's servers

The offline test and the UI statement together are consistent with real-time remote processing without retained audio, but that architecture remains an inference rather than a directly verified implementation fact.

## Noise behaviour

- Low-volume contradictory background speech did not contaminate the foreground user's transcript.
- At approximately equal or greater background volume, the user observed many transcription errors.
- This demonstrates useful foreground tolerance but not reliable speaker separation under competing speech of similar loudness.

## Evidence boundaries

### Directly observed

- Behaviour recorded in this dossier from the installed Windows alpha build.
- Text produced by Kivi and UI controls visible in supplied screenshots.
- Online/offline outcomes, restart outcomes, and cross-app labels.

### Reasonable inference, not proven fact

- Retrieval may use a stale semantic index after visible deletion.
- Settings failures may involve app-override and group-state synchronization.
- Audio likely depends on a remote real-time service in this build.
- Screen context may be unfinished or unsupported on Windows.

### Must not be claimed from these tests

- That all Kivi inference is on-device.
- That Kivi never transmits audio.
- That every platform has the Windows alpha defects.
- That public-review sentiment accurately represents the current build.
- That a specific database, vector store, model, or architecture is used internally.

## Questions for the applicant's independent Part One thinking

These are prompts only; they intentionally do not supply positioning or vision language.

1. Which observed behaviour made Kivi feel most valuable in ordinary daily work?
2. Which user should Kivi serve first, based on demonstrated strengths rather than theoretical capability?
3. What should Kivi remember, and what should remain ephemeral?
4. What level of provenance must accompany a recalled fact?
5. How should corrections, rejected ideas, uncertainty, and superseded plans be represented?
6. What should deletion mean across visible History, retrieval indexes, caches, and synced devices?
7. Which privacy choices should be defaults, and which should require explicit consent?
8. When should Kivi abstain instead of offering a fluent answer?
9. How should the product recover from a proper-noun or technical-identifier error?
10. Which capabilities are essential for a trustworthy first version, and which should be deferred?

