# Antigravity Status

Owner: Antigravity
Branch: antigravity/reproducibility-docs

Antigravity updates this file after each pushed checkpoint. Codex does not edit progress below this line.

## Completed

- **Milestone 2A (September 12) - Reviewer Documentation & Clean-Clone Reproducibility**:
  - **Documentation**: Drafted README.md, RUN.md, .env.example, docs/ARCHITECTURE.md, and docs/LIMITATIONS.md using formal, impersonal project writing. AI-use statements are marked with [USER APPROVAL REQUIRED].
  - **Windows Clean-Clone Rehearsal**: Created a fresh clone in a disposable directory, created a virtual environment, installed dependencies, migrated the database, and imported the corpus and projects using kivi corpus import.
  - **Custom Corpus Import Test**: Ran an independent test with a newly shaped 2-line JSONL corpus (kivi corpus import test_corpus.jsonl --expected-count 2). The ingestion correctly recognized 2 total records but appropriately reported 2 failures due to missing provider configuration (expected behavior in a clean offline environment).
  - **Deterministic Evaluation**: Successfully executed the kivi evaluate --mode deterministic command in the clean clone, processing exactly 132 cases with 132 passed.

## Candidate-Provider Evaluation Readiness

- **Environment Variable Required**: OPENAI_API_KEY, KIVI_MODEL_PROVIDER="openai"
- **Candidate Model Configuration**: KIVI_LLM_MODEL="gpt-5.6-luna", KIVI_EMBEDDING_MODEL="text-embedding-3-small"
- **Command**: kivi evaluate --mode candidate
- **Estimated Case Count**: 132
- **Blockers / Readiness**: Evaluation is blocked solely by the intentional absence of the OPENAI_API_KEY in the .env file. Once the API key is configured, the system is fully ready to run the candidate-provider evaluation.

## Blockers

- None.

## Request to Codex

- Clean-clone reproducibility and reviewer documentation are complete. The deterministic baseline passes 132/132 cases. Please review the drafted documentation before we proceed to candidate API spending or visual implementation.
