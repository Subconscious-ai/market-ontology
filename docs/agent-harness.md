# Agent Harness

This document is the agent-facing contract for Symphony/Codex work in this repo.
Keep `AGENTS.md` as the map and use this file for operational detail.

## Symphony Readiness Contract

Every Symphony task must end with:

- branch `codex/<linear-issue-id>-<short-slug>`
- committed local `HEAD`
- draft GitHub PR that references the Linear issue
- PR label `symphony`
- Linear `## Codex Workpad` comment
- validation command and pass/fail result
- pushed commit SHA
- GitHub check URL
- final Linear state `Human Review` only after `symphony-gate` is green

Failed or incomplete evidence goes to `Rework`, never `Done`.

## Validation Ladder

| Level | Command | Use |
|---|---|---|
| Preflight | `bash scripts/agent/preflight.sh` | Python import/dependency readiness before Codex starts |
| Fast | `bash scripts/agent/validate-fast.sh` | Default Symphony PR gate and normal full deterministic suite |
| Full | `bash scripts/agent/validate-full.sh` | Same deterministic suite; use for schema/contract changes |
| Smoke | `bash scripts/agent/smoke.sh` | Alias for fast validation |

Schema changes are cross-repo contract work. Land market-ontology first, then
coordinate dependent spice-harvester emitters and ai-chatbot consumers.

## Known Secrets

No secrets are required for fast validation. If future validation needs a
secret, keep it out of `validate-fast.sh` and document the secret here before
using it.

## Deploy Evidence

This repo does not deploy for normal Symphony PRs. Acceptable evidence:

- `symphony-gate` GitHub check URL
- CI check URL for schema/fixture validation

## Failure Buckets

Use these exact buckets in workpad blocker notes:

- `preflight`: Python setup/import readiness failed
- `validation`: schema, generated contract, unit, doc-rot, or compile checks failed
- `ci_check`: GitHub required check failed
- `ci_check_timeout`: required check did not finish inside the poll window
- `git_push`: branch push failed
- `github_pr`: draft PR creation or lookup failed
- `github_label`: `symphony` label could not be applied
- `evidence_gate`: missing workpad, PR, label, validation, SHA, or check evidence
- `codex_turn`: Codex turn failed or required unavailable human input
- `token_budget`: Symphony stopped the run for token budget
