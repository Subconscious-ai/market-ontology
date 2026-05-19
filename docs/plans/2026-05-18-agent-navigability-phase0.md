# Agent-Navigability — Phase 0 Execution Plan

Epic: `Subconscious-ai/market-ontology#90`. Phase 0 proves the agent-navigability
pattern in **market-ontology** before Phase 1 fans it out to spice-harvester,
ai-chatbot-native-sizzle, and causl.io.

## Status

- **System #1 — generated repo map** (`generate_repo_map.py` → `docs/REPO_MAP.md`,
  `--check`-gated): DONE — PR #92.
- **System #2 — generated repo index**: this plan.
- **System #4 — navigation eval** (the rollout gate): this plan.

## System #2 — `generate_repo_index.py`

A deterministic, AST-based generator → `docs/REPO_INDEX.md`: every Python module
under `poc_v1/`, `causal_dag_v1/`, and `scripts/`, listed with its public
top-level symbols (functions, classes — names not starting with `_`).

- Deterministic (sorted files, sorted symbols; no timestamp/commit-hash).
- `--check` mode, matching the `generate_*.py` idiom.
- Gated in `scripts/agent/validate-fast.sh` and `ci.yml`.
- Unit test for determinism + currency.

This is the committed, agent-agnostic file/symbol index — the reliable
replacement for the `/index` skill's local-only `PROJECT_INDEX.json` (which is
LLM-driven, Claude-only, and does not run regularly).

## System #4 — navigation eval (the rollout gate)

`scripts/agent/nav_eval.py` — a deterministic A/B over a fixed set of common
navigation questions. For each question it measures:

- **Coverage** — is the answer available directly from a generated asset
  (`REPO_MAP.md` / `REPO_INDEX.md`), with no code reading?
- **Context cost** — bytes an agent must read to answer **with** the assets
  (one asset file) vs **without** them (the union of source files that contain
  the answer).

Each task also asserts the asset currently contains the correct answer, so the
eval doubles as a rot gate: if an asset drifts, `nav_eval.py` fails.

## Rollout gate

Phase 1 (fan-out to spice-harvester / ai-chatbot-native-sizzle / causl.io)
proceeds **only if** `nav_eval.py` shows a material gain — high coverage and a
large context-cost reduction. No gain → the assets do not earn the fan-out.

## Execution

1. `generate_repo_index.py` + `docs/REPO_INDEX.md` + unit test + CI wiring.
2. `scripts/agent/nav_eval.py` + the task set; run it.
3. Record quantified results in the "Results" section below.
4. One PR, stacked on #92.

## Results

Run 2026-05-18, market-ontology, branch `feat/agent-nav/index-and-eval`.

**System #2 — repo index.** `scripts/generate_repo_index.py` → `docs/REPO_INDEX.md`:
20 Python modules with their public symbols, ~4 KB. Deterministic; `--check`-gated
in `validate-fast.sh` + `ci.yml`; covered by `tests/test_repo_index.py`. The gate
proved itself mid-build — adding `nav_eval.py` made the committed index stale and
`--check` failed until it was regenerated.

**System #4 — navigation eval (A/B).** `scripts/agent/nav_eval.py`, 8 common
navigation questions, deterministic with-vs-without-assets comparison:

| Metric | Without the assets | With the assets | Gain |
|---|---|---|---|
| Coverage — answerable with no source reading | 0 / 8 | 8 / 8 (100%) | — |
| Files to read to answer all 8 | 4 (and you must first find them) | 2 | 2x fewer |
| Bytes to read to answer all 8 | 41,172 | 6,469 | 6.36x less |

The byte ratio is a conservative lower bound: it does not count the grep/search
an agent needs *without* the assets just to discover which files hold the answer.
With the assets that search cost is zero.

**Live test — Claude.** Two fresh Claude subagents (Explore, general-purpose)
were asked a navigation question the assets answer: **0/2 used the generated
assets** — both read `schema.py` directly. Note: the Explore agent by design
does not load `CLAUDE.md` at all; the general-purpose agent loads it but ignored
the routing pointer.

**Live test — Codex.** A real `codex exec` run on the same question **did use
the asset**: it read `docs/REPO_MAP.md` (via the `AGENTS.md`->`CLAUDE.md`
routing), answered correctly, and cross-checked `schema.py`. Codex honors the
routing; Claude subagents are unreliable with it.

**Verdict — and the fix is NOT an auto-generated context block.** Web
best-practice research (InfoQ / arXiv, 2026) finds that auto-generated context
files degrade agent task success (~3% worse, +20% inference cost) and that
documenting derivable structure in `CLAUDE.md` is a liability. The proposed
"inline the map into CLAUDE.md" fix is therefore **not pursued** — it would
reinvent a wheel the research has already shown to be square. The
research-endorsed, measured mechanism (60-80% gains) is a code-intelligence MCP
server (Serena / Sourcegraph class) that exposes symbol-level navigation as
*tools* — which reaches even Explore-type agents that skip docs.

**Required before Phase 1 fan-out:** adopt a code-intelligence MCP as the
cross-agent navigation layer; keep the deterministic `--check`-gated
`REPO_MAP.md` / `REPO_INDEX.md` as its freshness substrate, and the lean
`CLAUDE.md` pointer (which already works for Codex). Re-validate, then fan out.

## Bake-off protocol — code-intelligence MCP (systems #5/#6)

Choose the navigation backend by measurement, not vendor claims. Vetted and
ready to run as a focused pass.

### Candidates
- **Serena** — LSP-backed symbol intelligence. MCP command via `uvx`
  (confirm exact subcommand with `--help`):
  `uvx --from git+https://github.com/oraios/serena serena-mcp-server`
- **codebase-memory-mcp v0.6.1** — AST knowledge graph, 14 tools. Install the
  release binary deliberately (the `curl | bash` installer was reviewed and is
  clean — signed-checksum binary, no sudo, no phone-home — but install by hand
  so the Codex config is edited deliberately):
  ```
  curl -fsSL -o /tmp/cmm.tar.gz \
    https://github.com/DeusData/codebase-memory-mcp/releases/download/v0.6.1/codebase-memory-mcp-linux-amd64.tar.gz
  # verify against checksums.txt from the same release, then extract to ~/.local/bin/
  ```
  Do **not** run `codebase-memory-mcp install -y` — it auto-rewrites agent
  configs. Configure deliberately instead.

### Config
Append an `[mcp_servers.*]` section to `~/.codex/config.toml` (it currently has
none — safe to append) for the Codex arm; add the same two entries to a
`.mcp.json` at the repo root for the Claude arm. Index the repo with each tool
before measuring.

### The eval
Reuse the `nav_eval.py` question set. Three arms: **baseline** (no MCP),
**Serena**, **codebase-memory-mcp**. For each, run the tasks via `codex exec`
and record: tokens-to-answer, answer correctness vs known gold (14 nodes /
18 edges / `SCHEMA_VERSION 1.6.0`), and whether the agent used the MCP's tools
unprompted. Baseline already measured: Codex with no MCP ≈ 21,124 tokens.

### Decision rule
Lowest tokens-to-correct-answer that an agent uses unprompted wins. Verify
codebase-memory-mcp's claimed 99.2% reduction against the measured baseline —
report the measured number, not the vendor's. The 3D-graph UI is a tiebreaker
only.

### Session constraint
The Codex arm runs headlessly (`codex exec` reads fresh config). The Claude arm
needs a **fresh** Claude Code session started with `.mcp.json` present — MCP
servers load at session start and cannot be hot-added to a running session.
