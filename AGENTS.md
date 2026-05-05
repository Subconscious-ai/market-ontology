# AGENTS.md - market-ontology

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

The authoritative repo guidance lives in [`CLAUDE.md`](./CLAUDE.md). It covers
the verify loop, schema-extension recipes, architectural invariants, and how
this repo fits into the three-repo Subconscious stack.

This file exists so the Codex harness lands on the same guidance as the Claude
harness.
