# Kivi Part Two Coordination Board

This directory is the asynchronous meeting point for Codex and Antigravity.

## Ownership

- `CODEX_STATUS.md`: Codex updates; Antigravity reads.
- `ANTIGRAVITY_STATUS.md`: Antigravity updates; Codex reads.
- `INTEGRATION_CONTRACT.md`: Codex maintains the frozen backend/frontend contract. Changes require an explicit contract decision.

Each status update must include the branch, exact commit, completed work, verification evidence, current work, blockers, and requests for the other agent. Status claims without a commit or command result are not treated as completed work.

## Exchange protocol

1. Commit owned work before requesting integration.
2. Push the owned branch.
3. Update and push the owned status file in the same branch.
4. State the exact commit that the other agent should integrate.
5. Fetch before reading the other agent's status.
6. Do not edit the other agent's status file.
7. Do not silently change shared schemas, API fields, statuses, or corpus contracts.
8. Record integration-test evidence after combining branches.

## Daily milestones

### September 10

Freeze contracts and prove one end-to-end path:

`take -> persisted memory -> scoped question -> typed cited answer -> browser display`

### September 11

Complete integrity behavior, all product surfaces, and the 500-record corpus.

### September 12

Complete evaluation, documentation, clean-clone verification, integration, and final submission freeze.

