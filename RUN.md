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

### Environment Variables

| Variable | Description |
|---|---|
| `KIVI_DATABASE_URL` | Database connection string (defaults to `sqlite:///./var/kivi.db`). |
| `KIVI_MODEL_PROVIDER` | Defines the provider backend (`openai` for live LLM extraction/answering, or `deterministic` for fixture-backed offline evaluation). |
| `OPENAI_API_KEY` | Your OpenAI API key (required when using `openai` provider). |
| `KIVI_LLM_MODEL` | The LLM model to use (e.g. `gpt-4o-mini`). |
| `KIVI_EMBEDDING_MODEL` | The embedding model to use (e.g. `text-embedding-3-small`). |
| `KIVI_LLM_INPUT_COST_PER_MILLION` | Optional: Configure cost accounting for input tokens. |
| `KIVI_LLM_OUTPUT_COST_PER_MILLION` | Optional: Configure cost accounting for output tokens. |
| `KIVI_EMBEDDING_COST_PER_MILLION` | Optional: Configure cost accounting for embedding tokens. |

> **Note:** For a fully local, deterministic offline review, modify `.env` to set `KIVI_MODEL_PROVIDER="deterministic"`.

## 3. Dependency Installation

Create a virtual environment and install dependencies. For running tests, ensure you install with the `[dev]` extras.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 4. Database Setup

Apply database migrations to initialize the SQLite database schema:
```bash
kivi db migrate
```

## 5. Seed and Corpus Import

Validate the included 500-record JSONL corpus, then import the projects and the corpus itself:

**Windows (PowerShell):**
```powershell
$env:KIVI_MODEL_PROVIDER="deterministic"
kivi corpus validate corpus/kivi_500.jsonl
kivi projects import corpus/projects.json
kivi corpus import corpus/kivi_500.jsonl
```

**macOS/Linux:**
```bash
KIVI_MODEL_PROVIDER="deterministic" kivi corpus validate corpus/kivi_500.jsonl
KIVI_MODEL_PROVIDER="deterministic" kivi projects import corpus/projects.json
KIVI_MODEL_PROVIDER="deterministic" kivi corpus import corpus/kivi_500.jsonl
```

> **Important Constraint on Deterministic Mode:** Deterministic extraction is fixture-backed by `corpus/gold_labels.jsonl` and exclusively supports the committed corpus Take IDs (e.g., `take_0001`). It does *not* imply general rule-based extraction for new payloads. Arbitrary new corpora require the configured OpenAI provider (`KIVI_MODEL_PROVIDER="openai"`) or matching gold labels.

## 6. Application Startup

Start the Kivi application:

**Windows (PowerShell):**
```powershell
$env:KIVI_MODEL_PROVIDER="deterministic"
kivi serve
```

**macOS/Linux:**
```bash
KIVI_MODEL_PROVIDER="deterministic" kivi serve
```

The application will run at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 7. Primary Interactions to Try

Open [http://127.0.0.1:8000/inbox](http://127.0.0.1:8000/inbox) in a browser.
1. Scope an unassigned memory take to a project.
2. View the timeline to see memory lifecycle states and evidence limits.
3. Use the briefing interface to ask grounded questions based on the ingested memory.
4. Correct a timeline entry and observe how the original memory is superseded and a new active memory is generated.
5. Revoke evidence from a memory and observe the results.

## 8. Importing an External Reviewer Corpus

The evaluator may translate its source records into this documented schema before import.

### External JSONL Schema
Each line in `external_takes.jsonl` is a JSON object with the following fields:
- `take_id` (string): Unique identifier for the take.
- `project_id` (string, nullable): ID of the project the take belongs to, or `null` if unassigned.
- `raw_asr` (string): Raw speech-to-text transcript.
- `formatted_text` (string): Formatted transcript with punctuation and casing.
- `source_application` (string): Name of the source application.
- `event_ts` (string): ISO 8601 timestamp with timezone.
- `metadata` (object): Arbitrary JSON object for metadata.

### External Project-Registry JSON Format
`external_projects.json` must follow this JSON format:
```json
[
  {
    "id": "project-example",
    "name": "Project Example",
    "aliases": ["Example"]
  }
]
```

### Mapping and Ingestion Rules
- **Explicit mapping rule:** Every non-null `project_id` in an external take must match an imported registry ID. Do not infer project scope from semantic similarity. If scope is unknown, use `null`; the record enters Inbox and creates no semantic memory until a normal user assigns scope.
- **Explicit provider rule:** Deterministic mode supports only committed gold-label fixtures. A novel reviewer corpus requires the configured OpenAI provider.

### Execution Commands

For a reviewer-provided 500-record corpus:

**Windows (PowerShell):**
```powershell
$env:KIVI_MODEL_PROVIDER="openai"
$env:OPENAI_API_KEY="your-api-key"
kivi db migrate
kivi corpus validate external_takes.jsonl
kivi corpus import external_takes.jsonl --projects external_projects.json
kivi inspect
kivi serve
```

**macOS/Linux:**
```bash
export KIVI_MODEL_PROVIDER="openai"
export OPENAI_API_KEY="your-api-key"
kivi db migrate
kivi corpus validate external_takes.jsonl
kivi corpus import external_takes.jsonl --projects external_projects.json
kivi inspect
kivi serve
```

## 9. Testing

Run the standard integration test suite:
```bash
pytest
```

## 10. Candidate Evaluation

The repository includes a 132-case deterministic evaluation suite. Run the evaluation against the offline deterministic backend:
```bash
kivi evaluate --mode deterministic
```

To test an actual AI candidate provider (requires setting `OPENAI_API_KEY` and changing `KIVI_MODEL_PROVIDER="openai"` in `.env`), run:
```bash
kivi evaluate --mode candidate
```

## 11. Inspecting Evaluation Results and Memory State

Check the aggregate numbers of memories, evidence, and projects:
```bash
kivi inspect
```
Evaluation output artifacts are placed in the `results/` directory as both JSON and Markdown files.

## 12. Resetting the Complete System

To wipe all local database changes and re-run migrations from scratch:
```bash
kivi db reset
```
