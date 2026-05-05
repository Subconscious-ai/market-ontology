# AGENTS.md — market-ontology

<<<<<<< HEAD
## Symphony Agent Entrypoints

Use these repo-owned scripts for deterministic setup and validation:

```bash
bash scripts/agent/preflight.sh       # Python dependency/import preflight
bash scripts/agent/validate-fast.sh   # default PR validation
bash scripts/agent/validate-full.sh   # same deterministic full suite
bash scripts/agent/smoke.sh           # alias for fast validation
```

Symphony/Codex PRs must use `codex/<issue-id>-<short-slug>` branches, open
draft PRs, add the `symphony` label, link the Linear issue, and record the
validation command/result plus check evidence in Linear. Treat schema changes
as cross-repo contract work and coordinate dependent PRs.
Exact validation ladder, known secrets, deploy evidence rules, and failure
buckets live in `docs/agent-harness.md`.

> Short table of contents for agents. The authoritative source for any claim
> below is the file or command it points to. If a pointer is wrong, fix the
> pointer — don't edit this file to match stale state.
=======
The authoritative agent guidance for this repo lives in [`CLAUDE.md`](./CLAUDE.md).
It covers the verify loop, schema-extension recipes, architectural invariants,
and how this repo fits into the three-repo Subconscious stack.
>>>>>>> d00f56c (chore(repo): prune scar tissue across docs and validator)

This file exists so the Codex harness (which looks for `AGENTS.md`) lands on
the same content as the Claude harness — one source of truth, no drift.
