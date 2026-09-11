# Kivi Semantic Memory System

Kivi is a project-scoped semantic memory demonstration built to evaluate extraction, retrieval, lifecycle management, and evaluation integrity for AI-driven memory systems. 

## Project Architecture

The architecture separates the deterministic memory lifecycle controls from the stochastic foundation models. Kivi strictly enforces scoping, updates, temporal validity, and evidence constraints independently of language models. For details on the architecture, consult [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick Start and Reviewer Operations

Please refer to [RUN.md](RUN.md) for complete instructions to run the application, load the corpus, and inspect evaluation results.

## Evaluation Results

Kivi includes two evaluation modes:
- **Deterministic**: Tests structural correctness, provenance, isolation, and lifecycle transitions without LLM stochasticity. Current runs score 132/132. Note: This mode does not test real-model response quality, only system-level logical integrity.
- **Candidate Provider**: Runs real LLM inferences against the pipeline to determine answer correctness, conflict detection, and real-world behavior. Requires external API keys.

## AI Use and Attribution

[USER APPROVAL REQUIRED]
The Kivi source code, tests, and schemas were implemented under the direction of Basavaraj A Naduvinamani with extensive collaboration and code generation by Antigravity and Codex models. All architectural decisions, testing paradigms, and evaluation results are the responsibility of the primary human author.

## Limitations

Please read [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for details on expected scaling constraints, missing enterprise features, and the bounds of the deterministic test environments.
