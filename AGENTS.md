# AGENTS.md — market-ontology

> Short table of contents for agents. The authoritative source for any claim
> below is the file or command it points to. If a pointer is wrong, fix the
> pointer — don't edit this file to match stale state.

## What this repo is

The canonical Pydantic schema for the Subconscious knowledge graph:
**9 node types, 9 edge types**. Installed by sibling repos as
`pip install "market-ontology @ git+https://github.com/Subconscious-ai/market-ontology"`.
Load-bearing — every write across the stack validates through here.

## Where things live

| What | Where |
|---|---|
| Schema (Pydantic models, NODE_MODELS/EDGE_MODELS) | `poc_v1/ontology/schema.py` |
| JSON schema dumps for TS/docs consumers | `poc_v1/ontology/{node,edge}_schemas.json` |
| Reference fixtures (one JSONL per label) | `poc_v1/kg_seed/*.jsonl` |
| Validator (CI entry point) | `scripts/validate_kg_seed.py` |
| Doc-rot guard | `scripts/check-doc-rot.sh` |
| CI workflow | `.github/workflows/ci.yml` |
| Cross-repo contract | `../ai-chatbot/docs/three-repo-handshake.md` |

## How to verify your work (runs in <30s)

```bash
python scripts/validate_kg_seed.py        # Pydantic-validates every kg_seed/*.jsonl
bash scripts/check-doc-rot.sh             # Markdown guard
python -m py_compile poc_v1/ontology/schema.py   # import-time sanity
```

If any of these fail, do not open a PR. Fix first.

## How to extend (recipes)

**Add a new node type:**
1. Add the Pydantic model to `poc_v1/ontology/schema.py`.
2. Register it in `NODE_MODELS` and bump `SCHEMA_VERSION`.
3. Create at least one fixture line in `poc_v1/kg_seed/<new_label>s.jsonl`.
4. Map the filename in `scripts/validate_kg_seed.py::FIXTURES`.
5. Run the verify loop above.

**Add a new edge type:** same pattern via `EDGE_MODELS` +
`edges_<from>_<rel>_<to>.jsonl`.

**Rename a field:** breaking change — bump `SCHEMA_VERSION` and coordinate
with spice-harvester (`lib/emit_kg_seed.py`) and ai-chatbot (graph renderer)
in the same PR round.

## Architectural invariants (do not break)

- **One source of truth for shape**: Pydantic models in `schema.py`. JSON
  schema files under `poc_v1/ontology/*.json` are generated artifacts — if
  they drift, regenerate from the Pydantic models; do not hand-edit.
- **Fixtures must validate**: `scripts/validate_kg_seed.py` is CI's red button.
- **No orphan fixtures**: every `kg_seed/*.jsonl` must be mapped in `FIXTURES`.
- **Node records** are `{"id": ..., "properties": {...}}`. **Edge records**
  are `{"start_id": ..., "end_id": ..., "properties": {...}}`. Flat is a
  bug — see `scripts/validate_kg_seed.py` for the payload shape.

## How to ship

- Branch name: `feat/<short>` or `chore/<short>` or `fix/<short>`.
- Keep PRs focused: schema change + fixture update + validator test is
  one PR. Do not bundle unrelated fixes.
- CI must be green before merge. No `--no-verify` unless the user says so.
- Breaking schema changes get their own PR with a migration note in the
  body.

## See also

- `CLAUDE.md` — identical content to this file, kept as a Claude Code shim.
- `../ai-chatbot/docs/three-repo-handshake.md` — how this repo fits into
  the three-repo stack.
