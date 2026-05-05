# Market Simulation Ontology — v1 POC

## Purpose

This package is the minimal ontology that sits between:

1. A wiki-style market research agent (+ executive interview input)
2. The Subconscious.ai discrete choice experiment engine

The ontology is **context for the experiment**, not the experiment itself. Subconscious owns experiment design and causal estimation. This repo owns the structured context that feeds Subconscious and the structured results that come back.

## Scope

- Single customer, single company, 12-month horizon.
- POC-grade. See `v2_spec.md` for the parking lot of things deliberately cut.

## Core model

**Stakeholder archetypes + Offering attributes + Market context → Transition between AARRR stages → Part-worth estimates back from Subconscious.**

## Stack

- **FalkorDB-compatible property graph** as the store.
- **Pydantic** at the write boundary for schema enforcement.
- **Splink** (separate job) for entity resolution on Offerings and StakeholderArchetypes.
- Deployment-specific import/export over validated JSONL fixtures.
- **Postgres + pg_vector** (optional, separate) if the research agent needs semantic retrieval over Evidence excerpts.
- **Graphiti is deliberately not in v1.** Revisit in v2 if research-agent ingestion quality plateaus.

## Node types (13)

| Node | Purpose |
|---|---|
| Market | Scope boundary for every query |
| Stage | AARRR stage as a first-class node |
| Transition | The state change being modeled |
| StakeholderArchetype | Customer or competitor-side archetype |
| Offering | Object of study (product, service, SKU) |
| Attribute | Dimension of an Offering that can be varied |
| AttributeLevel | Plausible level for an Attribute in a Market/period |
| Trait | Dimension of a StakeholderArchetype used to describe a persona |
| TraitLevel | Plausible level for a Trait in a Market/period |
| Evidence | Source grounding for any node |
| Estimate | Part-worth or other quantity returned from Subconscious |
| Company | Organization that offers one or more Offerings |
| ExperimentRun | Execution record tying an ontology snapshot to SuperEgo/W&B artifacts |

## Edge types (13)

```
Transition -[:FROM]-> Stage
Transition -[:TO]-> Stage
Transition -[:IN_MARKET]-> Market
Transition -[:RELEVANT_TO]-> StakeholderArchetype
Transition -[:ABOUT]-> Offering

Offering -[:HAS_ATTRIBUTE]-> Attribute
Offering -[:OFFERED_BY]-> Company
Attribute -[:HAS_LEVEL]-> AttributeLevel
StakeholderArchetype -[:HAS_TRAIT]-> Trait
Trait -[:HAS_LEVEL]-> TraitLevel
Attribute -[:RELEVANT_AT {score, valid_from, valid_to, evidence_ids}]-> Stage

Evidence -[:SUPPORTS]-> *
Estimate -[:ABOUT]-> *
ExperimentRun -[:CONSUMED]-> *
ExperimentRun -[:PRODUCED]-> Estimate
```

## Golden rules

1. **No probabilities or part-worths on ontology nodes.** Those are Estimates. Estimates point at ontology nodes; they don't mutate them.
2. **Competitor combinations, treatments, and choice tasks live in Subconscious, not here.** The ontology provides attributes, levels, archetypes, and context. Subconscious composes experiments.
3. **If a value is conditional on model, period, or experiment, it is an Estimate.**
4. **Every node has `schema_version`.** Every Estimate has `ontology_snapshot_hash`.
5. **Temporal validity (`valid_from`, `valid_to`) applies to AttributeLevel, TraitLevel, RELEVANT_AT edges, Estimate, and Evidence.** Not to stable definitional nodes (Stage, Market scope, Transition definition).

## Pipeline

1. Research agent + executive interview extract node and edge candidates with evidence into JSONL.
2. Pydantic validates at the write boundary.
3. The graph-store adapter imports validated JSONL into FalkorDB.
4. Splink runs entity resolution on Offerings and StakeholderArchetypes after each ingestion pass.
5. Customer-facing products read from the property graph.
6. Experiment context is projected to JSON (see `contracts/experiment_context.schema.json`) and sent to Subconscious.
7. SuperEgo/W&B run-local IDs are bound back to ontology IDs through `contracts/experiment_run_mapping.schema.json`.
8. Subconscious returns results (see `contracts/experiment_results.schema.json`) which land as Estimate nodes linked to an ExperimentRun.

## Twenty projection

`ontology/twenty_projection.json` is the source manifest for the Twenty projection. `ontology/twenty_app_contract.json` is generated from it and exposes Company, Product, and Persona as primary business surfaces while preserving support objects and sync metadata for provenance.

## SuperEgo projection

`ontology/super_ego_projection.json` maps ontology nodes to SuperEgo API surfaces and W&B run/artifact metadata. It is an integration contract only; API credentials stay outside this repo.

## Causal projection artifacts

Causal DAGs, market signals, normalized experiment results, and recommendations are versioned artifacts under `contracts/`. They reference ontology node IDs and `ontology_snapshot_hash`; they do not add causal edges to the core graph.

`../docs/causal_projection_library_grounding.md` defines how these artifacts map to NetworkX, CausalNex, EconML, CausalFlow, RDF/RDFLib, W&B, and FalkorDB. The repo uses `jsonschema[format]` and NetworkX for CI/dev validation only; the heavier causal libraries are not core runtime dependencies.

## What changed from v0

See `MIGRATION.md`.

## What's cut and why

See `v2_spec.md`.
