# Agent routing — Codex vs Claude

Which agent should take a ticket. A starting heuristic (v0) — instrument and refine.
Destined for the `agent-system` repo as cross-repo best practice.

## The distinction

**Codex — specification-follower.** Treats `AGENTS.md`, contracts, runbooks, and
the `scripts/agent/` harness as authoritative instructions and executes them
literally. Low-variance and reliable on well-specified work. Risk: if the spec
is stale or wrong, it follows it off a cliff — less likely to challenge the
premise.

**Claude — intent-reasoner.** Reasons from the task and from source-of-truth
(the code), treats docs as secondary and possibly stale. Catches a wrong spec,
debugs root causes, handles ambiguity, makes judgment calls. Risk: may deviate
from a strict convention, or "improve" what you wanted left alone.

Observed this session: asked the same navigation question, Codex followed the
`CLAUDE.md` "read `REPO_MAP.md`" pointer and used the generated asset (4/4
runs); Claude reasoned "source is truth" and read `schema.py` directly (0/5
used the asset). Neither is wrong — they are different postures, and each is a
strength in its lane.

## The rubric — apply when writing the ticket

1. **Fully specified?** Is there a contract, `AGENTS.md` procedure, runbook, or
   harness task-type it fits — and could you write the acceptance test before
   starting? → **Codex.**
2. **Judgment needed?** Debugging / root-cause, design, ambiguous scope, or
   reasoning about *why* where the spec is incomplete or might itself be wrong?
   → **Claude.**
3. **Unsure?** → **Claude.** It degrades more gracefully on a mis-route — it
   reasons; a mis-routed Codex executes a bad spec literally.

## Lanes

**Codex lane** — Symphony task types (`schema-contract`, `ontology-fixture`,
`docs-canary`, `ci-harness`, `consumer-contract`), mechanical codegen against a
strict contract, regenerate-and-`--check`, repetitive structured edits, fixture
and test scaffolding, conventional refactors with a clear before/after. Branch
`codex/<issue>-<slug>`; runs the `scripts/agent/` harness.

**Claude lane** — investigation and debugging, architecture and design,
ambiguous scoping, schema/contract *design* (as opposed to propagation),
cross-system reasoning, anything where following a stale doc would be the
failure mode.

## Mechanism

- Add a `route:` line to every non-trivial ticket: `codex` | `claude` | `either`.
  Set it at creation with the rubric above. Put it in the issue template so it
  is unavoidable. It is a recommendation, not a lock — a human can override.
- Route by task *type*, not by size or repo.
- A large ticket often splits along the routing seam: contract *design* is
  Claude, mechanical *propagation* to consumers is Codex. Split big tickets
  there, and route each part.
- Do **not** build an LLM auto-router yet — premature. Run the rubric manually,
  record `route` + outcome on ~50 tickets, then the data justifies automation.
- Anti-pattern: forcing convergence — over-constraining Claude to act like
  Codex, or expecting Codex to challenge a spec. Use the grain of each tool.

## Status

v0 heuristic — drawn from a small in-session sample plus general priors, not a
validated law. Calibrate against real ticket outcomes; revise as the sample
grows. First seed artifact for the `agent-system` repo.
