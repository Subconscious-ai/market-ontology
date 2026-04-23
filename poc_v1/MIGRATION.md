# Migration — v0 to v1 (and v1.0 → v1.1)

This document records what changed between the initial POC scaffolding and the v1 ontology, and why. Keep this file. Future schema migrations should follow the same pattern.

## v1.0 → v1.1 (2026-04-23) — add Company node + OFFERED_BY edge

**Backwards-compatible.** No fixture rewrites required; existing `kg_seed/*.jsonl` continues to validate. `SCHEMA_VERSION` bumped `1.0.0 → 1.1.0`.

### Change

- New node type `Company` with minimal props (`id`, `name`, `domain?`, `definition?`). No funding / size / industry fields — add when a consumer query needs them.
- New edge type `OFFERED_BY`: `Offering → Company`. This is the programmatic rollup link: `AttributeLevel → (HAS_LEVEL^-1) → Attribute → (HAS_ATTRIBUTE^-1) → Offering → (OFFERED_BY) → Company`.
- `Offering.company_name` string prop is kept for backwards compat. It will be deprecated in v2 — consumers should start migrating to the edge-based lookup.

### Why

Rehoboam's `attributes-levels/orthogonal` endpoint generates Attributes+Levels per product. Downstream DCE queries aggregate those up to the Company level ("what are all of Acme's attributes across their full product portfolio?"). Doing this via `company_name` string matching is fragile; making Company a first-class node with `OFFERED_BY` edges gives us clean graph traversal and sets up proper entity resolution (Splink on Company.name later).

### Mechanics for consumers

- **spice-harvester:** `lib/emit_kg_seed.py` should derive Company + OFFERED_BY records from each Offering's existing `company_name` string on every write. No new LLM call required — pure transformation. (Paired PR lands at the same time as this bump.)
- **ai-chatbot:** no immediate changes required. Graph renderer will start receiving Company nodes + OFFERED_BY edges as slugs re-ingest.
- **Neo4j:** no migration needed — optional node type, missing values are fine.

### Non-goals

- Company-side props beyond `id / name / domain / definition`. YAGNI.
- Removing `Offering.company_name`. Keep both; remove in v2 cleanup.
- `Company → Market` edge. Add when a consumer query needs it.

## Summary

The v0 scaffolding tried to do two things at once: model a business ontology AND run its own causal analysis via DoWhy. Subconscious.ai owns the causal analysis. The v1 rewrite makes the ontology a pure context store that serves experiment specs to Subconscious and receives estimates back.

Net effect: schema got tighter, moving parts reduced, boundary with Subconscious made explicit.

## What was cut from v0 and why

| Removed | Why |
|---|---|
| `causality/choice_dag.py`, `activation_dag.py`, `retention_dag.py` | DAGs live inside Subconscious. Duplicating them here creates two causal systems that can disagree. |
| `causality/dowhy_runner.py`, `dowhy_estimands.yaml` | DoWhy is Subconscious's job, not ours. |
| `causality/causal_results.jsonl` | Causal results land as `Estimate` nodes via the results contract, not as a side file. |
| `simulation/simulation_rows.jsonl`, `simulation/simulation_rows.parquet` | Row-level tabular projection is an artifact of doing our own causal modeling. Subconscious generates its own tasks from the experiment context JSON. |
| `data_contracts/simulation_row.schema.json` | Replaced by `contracts/experiment_context.schema.json` and `contracts/experiment_results.schema.json`. |
| `data_contracts/causal_variable_map.yaml` | Mapping between graph and tabular layer is obsolete — Subconscious consumes the context JSON directly. |
| `data_contracts/metric_definitions.yaml` | Metric formulas as prose strings weren't useful. Deferred to v2 with an executable DSL. |

## What was renamed or restructured

| v0 | v1 | Why |
|---|---|---|
| `Stakeholder` | `StakeholderArchetype` | "Archetype" makes clear this is a type, not a person. Enables competitor-side archetypes cleanly. |
| `Context` (god-object with period + budget_state + regulatory_pressure + channel + treatment_label) | `Market` with `context_factors` JSONB + treatment moved out entirely | The v0 Context conflated environment, channel, time index, and experiment treatment. In v1, treatments are Subconscious's concern and never land on the ontology. |
| Offering attributes as flat properties (`price`, `brand_strength`, `provenance_visibility`, `setup_days`) | `Attribute` and `AttributeLevel` nodes | Attributes and their levels are what DCE tests. Modeling them as first-class nodes lets evidence attach to specific levels and lets the experiment designer enumerate the design space. |
| Stakeholder sensitivities as properties (`price_sensitivity`, `brand_sensitivity`, `trust_sensitivity`) | Removed. Sensitivities land as `Estimate` nodes. | These are posterior quantities from choice models. Storing them on ontology nodes violates the "no conditional values on ontology" rule. |
| Stage as a string property on `Transition` | `Stage` as first-class node with FROM/TO edges | Enables attribute relevance queries keyed by stage. Clean Bloom UX. |
| No market node; market implicit in Context | `Market` as first-class node | Every query is market-scoped. Making it explicit unlocks multi-market futures. |

## What was added

| Added | Why |
|---|---|
| `Attribute` and `AttributeLevel` nodes | Core DCE primitives. |
| `Stage` as a node | Enables `RELEVANT_AT` edges and clean transition endpoints. |
| `Market` as a node | Scope boundary for every query. |
| `Estimate` as a node | Target landing pad for Subconscious results. Keeps estimates versioned and doesn't mutate ontology. |
| `RELEVANT_AT` edge with `score`, `valid_from`, `valid_to`, `evidence_ids` | Temporal relevance of attributes at stages is the hardest query the experiment designer makes — make it fast. |
| `ontology_snapshot_hash` on every Estimate | Results are always interpretable against the ontology state they were computed on. |
| `schema_version` on every node and edge | Enables future migrations. |
| `extracted_claim`, `retrieval_query`, `extractor_version` on Evidence | Better provenance for research-agent-driven ingestion. |
| Pydantic validation at the write boundary (`ontology/schema.py`) | Single source of truth for the schema. No raw Cypher writes from the research agent. |
| Contracts: `experiment_context.schema.json`, `experiment_results.schema.json` | Makes the Subconscious boundary explicit and versioned. |

## Things that stayed the same

- `Evidence` as a node with `SUPPORTS` to any target.
- Transition as a first-class node, not an edge.
- APOC-based JSONL import pattern.
- Neo4j + Bloom for visualization.

## Tooling changes

- **Graphiti: not used in v1.** Revisit in v2 if research-agent ingestion quality plateaus.
- **Splink for entity resolution** on Offerings and StakeholderArchetypes — runs as a batch job after ingestion.
- **Pydantic** at the write boundary as the single schema source of truth.

## Migration steps for existing data (if any seed data was loaded)

1. Drop the old database or migrate to a fresh one. The schema differences are too large to auto-migrate cleanly for POC seed data. Fresh start is faster and safer.
2. Apply `neo4j/constraints.cypher`.
3. Validate all seed JSONL through `ontology/schema.py` before loading.
4. Run `neo4j/import_jsonl.cypher` with APOC.
5. Run Splink dedupe on Offerings and StakeholderArchetypes.
6. Open Bloom and confirm the search phrases in `neo4j/bloom_search_phrases.cypher` return expected results.

## Breaking changes the research agent needs to handle

If you already wired a research agent against v0:

- Extraction output format changed. Node payloads now require `schema_version`. See `ontology/node_schemas.json`.
- `Stakeholder` extractor must be renamed to `StakeholderArchetype` and set `archetype_type`.
- `Context` extractor must be split into: `Market` (one per ontology) with `context_factors` dict, plus nothing for treatment (Subconscious handles).
- Offering extractor must now also produce `Attribute` and `AttributeLevel` candidates instead of flat props.
- Stakeholder sensitivity extraction should be dropped entirely. Those are experiment outputs, not research inputs.
