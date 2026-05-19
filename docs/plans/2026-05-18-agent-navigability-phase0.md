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

**Live test — do agents actually use the assets?** Two fresh agents (one
Explore, one general-purpose) were each asked a navigation question the assets
answer directly. Result: **0 of 2 used the generated assets.** Both went
straight to `poc_v1/ontology/schema.py` and read it. The `CLAUDE.md`
"read REPO_MAP.md first" routing line did not change behavior.

**Rollout-gate verdict: NOT passed.** The deterministic A/B proves the *ceiling*
(6.36x context reduction *if* the asset is used). The live test shows agents do
not autonomously reach for a standalone `docs/REPO_MAP.md` — the potential gain
is currently left on the table. A separate file is the wrong delivery vehicle.
N=2 and both were quick-question tasks, so this is a strong signal rather than
proof, but the burden is on "agents will use it" and so far it is failing.

**Required before Phase 1 fan-out:** deliver the map *content* through the
channel agents already auto-read — generate it into a marked block inside
`CLAUDE.md` (auto-loaded by Claude; `AGENTS.md` / `GEMINI.md` symlink to it), or
inject it via a SessionStart hook. Freshness (`--check`) and delivery (getting
the agent to read it) are separate problems; Phase 0 solved the first, not the
second. Re-run the live test; fan out only once agents demonstrably use it.
