# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

`market-ontology` is the canonical Pydantic schema enforcer for every Subconscious system — research pipeline, visualization, interview extraction, agent outputs, DB projection. It sits between a wiki-style research agent + executive interview (input) and the Subconscious.ai discrete choice experiment engine (consumer). The ontology is **context for the experiment, not the experiment itself.** Subconscious owns experiment design and causal estimation. This repo owns the structured context feeding Subconscious and the structured results coming back.

One leg of the three-repo Subconscious stack ([spice-harvester](../spice-harvester/CLAUDE.md) writes → `market-ontology` validates → [ai-chatbot](../ai-chatbot/CLAUDE.md) reads). See `../ai-chatbot/docs/three-repo-handshake.md` for the full contract.

## Commands

```bash
# Pydantic-validate every kg_seed/*.jsonl fixture (CI entry point)
python scripts/validate_kg_seed.py

# Markdown doc-rot guard (fails on stale paths or forbidden substrings)
bash scripts/check-doc-rot.sh

# Schema import sanity
python -m py_compile poc_v1/ontology/schema.py

# Generated JSON schema sanity
python -c "import json; [json.load(open(p)) for p in ('poc_v1/ontology/node_schemas.json','poc_v1/ontology/edge_schemas.json')]"
```

No `pyproject.toml` / `setup.py` / `package.json`. Only runtime dep is Pydantic ≥2.

## Install as a dependency (from the other repos)

```bash
pip install "market-ontology @ git+https://github.com/Subconscious-ai/market-ontology"
# or local editable
pip install -e /path/to/market-ontology
```

## Architecture

### Schema (the only source of truth)

`poc_v1/ontology/schema.py` defines Pydantic models, `NODE_MODELS` / `EDGE_MODELS` registries, and `SCHEMA_VERSION`.

**9 node types:** `Market`, `Stage`, `Transition`, `StakeholderArchetype`, `Offering`, `Attribute`, `AttributeLevel`, `Evidence`, `Estimate`.

**10 edge types:**
```
Transition -[:FROM]-> Stage
Transition -[:TO]-> Stage
Transition -[:IN_MARKET]-> Market
Transition -[:RELEVANT_TO]-> StakeholderArchetype {confidence}
Transition -[:ABOUT]-> Offering
Offering -[:HAS_ATTRIBUTE]-> Attribute
Attribute -[:HAS_LEVEL]-> AttributeLevel
Attribute -[:RELEVANT_AT {score, valid_from, valid_to, evidence_ids}]-> Stage
Evidence -[:SUPPORTS]-> * {confidence, support_type}
Estimate -[:ABOUT]-> * {target_node_type}
```

Enums live in `poc_v1/ontology/enums.yaml` (StageName, ArchetypeType, AttributeDataType, EvidenceSourceType, EstimateType). Keep `enums.yaml` and `schema.py` in sync by hand — the YAML is human reference, the Python is authoritative.

`node_schemas.json` and `edge_schemas.json` are **generated artifacts**. Regenerate when schema changes; never hand-edit.

### Directory Layout

```
poc_v1/
├── ontology/
│   ├── schema.py              ← Pydantic models + NODE_MODELS/EDGE_MODELS + SCHEMA_VERSION (authoritative)
│   ├── node_schemas.json      ← Generated from schema.py
│   ├── edge_schemas.json      ← Generated from schema.py
│   ├── enums.yaml             ← Human reference enums (keep in sync with schema.py)
│   ├── ontology_spec.md       ← Design doc: 9 nodes, 10 edges, ingestion rules
│   ├── v2_spec.md             ← Parking lot for things cut from v1
│   └── MIGRATION.md           ← Changes from v0
├── kg_seed/                   ← Reference fixtures, one JSONL per node/edge label
│   ├── markets.jsonl, stages.jsonl, transitions.jsonl, ...
│   └── edges_transition_*.jsonl, edges_estimate_*.jsonl, ...
├── contracts/                 ← Boundary contracts with Subconscious
│   ├── experiment_context.schema.json  ← ontology → Subconscious
│   └── experiment_results.schema.json  ← Subconscious → ontology
└── neo4j/
    ├── constraints.cypher, import_jsonl.cypher, bloom_search_phrases.cypher

scripts/
├── validate_kg_seed.py        ← CI: iterates FIXTURES map, Pydantic-validates each JSONL
└── check-doc-rot.sh

.github/workflows/ci.yml       ← 4-step: JSON syntax, kg_seed validation, import sanity, doc-rot
```

### Write boundary (how kg_seed flows)

spice-harvester emits `output/<slug>/kg_seed/*.jsonl` via its `lib/emit_kg_seed.py` → `python scripts/validate_kg_seed.py` Pydantic-validates → APOC imports the JSONL into Neo4j. Every node payload is `{"id": ..., "properties": {...}}`; every edge payload is `{"start_id": ..., "end_id": ..., "properties": {...}}`.

## Golden Rules

1. **No probabilities or part-worths on ontology nodes.** Those are `Estimate` nodes. Estimates point at ontology nodes; they don't mutate them.
2. **Competitor combinations, treatments, and choice tasks live in Subconscious, not here.** The ontology provides attributes, levels, archetypes, and context. Subconscious composes experiments.
3. **If a value is conditional on model, period, or experiment, it is an `Estimate`.**
4. **Every node has `schema_version`. Every `Estimate` has `ontology_snapshot_hash`.**
5. **Temporal validity** (`valid_from`, `valid_to`) applies to `AttributeLevel`, `RELEVANT_AT` edges, `Estimate`, `Evidence`. Not to stable definitional nodes (`Stage`, `Market`, `Transition`, `Attribute`).

## Extending the Schema

1. Edit `poc_v1/ontology/schema.py`: add the Pydantic model, register in `NODE_MODELS` or `EDGE_MODELS`, bump `SCHEMA_VERSION`.
2. Create a matching fixture at `poc_v1/kg_seed/<label>s.jsonl` (or `edges_<label>.jsonl`).
3. Add the filename → model mapping to `scripts/validate_kg_seed.py::FIXTURES`. Unmapped files fail CI.
4. Regenerate `node_schemas.json` / `edge_schemas.json` if consumers depend on them.
5. Run all four commands in the section above. Do not `--no-verify`.
6. Breaking schema changes require coordinated PRs in `spice-harvester` (update `lib/emit_kg_seed.py`) and `ai-chatbot` (update type hints in `app/(chat)/api/interview-sse/` and any graph renderers).

## Conventions (from AGENTS.md)

- **Branches:** `feat/<short>`, `chore/<short>`, `fix/<short>`.
- **One concern per PR:** schema change + fixture + validator test = one PR.
- **No orphan fixtures** — every `kg_seed/*.jsonl` must appear in `FIXTURES`.
- **Fixtures must validate before opening a PR.**

## Stack (downstream, not implemented here)

Consumers operate this stack on top of the schema:
- **Neo4j** as the graph store. **Bloom** for customer-facing visualization. **APOC** for JSONL import/export.
- **Splink** (separate job, in spice-harvester) for entity resolution on `Offering` and `StakeholderArchetype` after each ingestion pass.
- **Postgres + pgvector** (optional, separate) if the research agent needs semantic retrieval over `Evidence` excerpts.
- **Graphiti** is deliberately not in v1. Revisit in v2 if research-agent ingestion quality plateaus.
