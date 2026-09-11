# Running Kivi

This guide describes how to run a complete clean installation, evaluation, and manual testing cycle for Kivi.

## 1. Requirements

- Python 3.11 or 3.12 (Python 3.11+ is required)
- Git

## 2. Environment Setup

Clone the repository and enter the directory:
```bash
git clone https://github.com/basavarajnaduvinamani/sarvam-kivi-golden-goose.git kivi
cd kivi
```

Create a `.env` file from the example:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

> **Note:** For a fully local, deterministic offline review, modify `.env` to set `KIVI_MODEL_PROVIDER="deterministic"`.

## 3. Dependency Installation

Create a virtual environment and install dependencies.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 4. Database Setup

Apply database migrations to initialize the SQLite database schema:
```bash
kivi db migrate
```

## 5. Seed and Corpus Import

Validate the included 500-record JSONL corpus, then import the projects and the corpus itself:
```bash
kivi corpus validate corpus/kivi_500.jsonl
kivi projects import corpus/projects.json
kivi corpus import corpus/kivi_500.jsonl
```

## 6. Application Startup

Start the Kivi application:
```bash
kivi serve
```

The application will run at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 7. Primary Interactions to Try

Open [http://127.0.0.1:8000/inbox](http://127.0.0.1:8000/inbox) in a browser.
1. Scope an unassigned memory take to a project.
2. View the timeline to see memory lifecycle states and evidence limits.
3. Use the briefing interface to ask grounded questions based on the ingested memory.
4. Correct a timeline entry and observe how the original memory is superseded and a new active memory is generated.
5. Revoke evidence from a memory and observe the results.

## 8. Importing Another Corpus

You can independently construct and import a small JSONL corpus conforming to the schema:
```bash
kivi corpus import path/to/your_corpus.jsonl
```

## 9. Candidate Evaluation

The repository includes a 132-case deterministic evaluation suite. Run the evaluation against the offline deterministic backend:
```bash
kivi evaluate --mode deterministic
```

To test an actual AI candidate provider (requires setting `OPENAI_API_KEY` and changing `KIVI_MODEL_PROVIDER="openai"` in `.env`), run:
```bash
kivi evaluate --mode candidate
```

## 10. Inspecting Evaluation Results and Memory State

Check the aggregate numbers of memories, evidence, and projects:
```bash
kivi inspect
```
Evaluation output artifacts are placed in the `results/` directory as both JSON and Markdown files.

## 11. Resetting the Complete System

To wipe all local database changes and re-run migrations from scratch:
```bash
kivi db reset
```
