# Agent Observability

This repo must leave enough evidence for a human or Symphony to understand an
agent run without replaying the whole conversation.

## Required Run Evidence

Each Symphony PR must expose:

- Linear `## Codex Workpad` with branch, commit SHA, PR URL, validation result,
  check URL, and blocker notes when applicable
- draft PR with `symphony` label and Linear issue reference
- `symphony-gate` GitHub check URL
- schema/fixture CI check URL
- local validation command copied verbatim from `scripts/agent/*`

## Where To Look

| Signal | Location |
|---|---|
| Agent instructions | `AGENTS.md` |
| Harness contract | `docs/agent-harness.md` |
| Readiness check | `bash scripts/agent/readiness.sh` |
| Fast validation | `bash scripts/agent/validate-fast.sh` |
| Full validation | `bash scripts/agent/validate-full.sh` |
| GitHub gate | `.github/workflows/symphony-gate.yml` |
| Contract smoke | `bash scripts/agent/smoke.sh` |

## Measurement Fields

For canaries and real tasks, record these fields in the Linear workpad or the
Symphony run trace:

- repo
- Linear issue
- branch
- PR URL
- validation command
- validation duration
- uncached tokens
- total tokens
- tool-call count
- retry_count
- manual_rescue_count
- failure bucket
- final Linear state

## Static Proof Markers

- BEC-1805: removable Symphony harness observability marker.

## Failure Buckets

Use the buckets from `docs/agent-harness.md`. Do not invent new labels unless
the harness docs and tests are updated in the same PR.
