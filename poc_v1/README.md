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

- **Neo4j** as the store. Bloom for customer-facing visualization.
- **Pydantic** at the write boundary for schema enforcement.
- **Splink** (separate job) for entity resolution on Offerings and StakeholderArchetypes.
- **APOC** for JSONL import/export.
- **Postgres + pg_vector** (optional, separate) if the research agent needs semantic retrieval over Evidence excerpts.
- **Graphiti is deliberately not in v1.** Revisit in v2 if research-agent ingestion quality plateaus.

## Node types (9)

| Node | Purpose |
|---|---|
| Market | Scope boundary for every query |
| Stage | AARRR stage as a first-class node |
| Transition | The state change being modeled |
| StakeholderArchetype | Customer or competitor-side archetype |
| Offering | Object of study (product, service, SKU) |
| Attribute | Dimension of an Offering that can be varied |
| AttributeLevel | Plausible level for an Attribute in a Market/period |
| Evidence | Source grounding for any node |
| Estimate | Part-worth or other quantity returned from Subconscious |

## Edge types (10)

```
Transition -[:FROM]-> Stage
Transition -[:TO]-> Stage
Transition -[:IN_MARKET]-> Market
Transition -[:RELEVANT_TO]-> StakeholderArchetype
Transition -[:ABOUT]-> Offering

Offering -[:HAS_ATTRIBUTE]-> Attribute
Attribute -[:HAS_LEVEL]-> AttributeLevel
Attribute -[:RELEVANT_AT {score, valid_from, valid_to, evidence_ids}]-> Stage

Evidence -[:SUPPORTS]-> *
Estimate -[:ABOUT]-> *
```

## Golden rules

1. **No probabilities or part-worths on ontology nodes.** Those are Estimates. Estimates point at ontology nodes; they don't mutate them.
2. **Competitor combinations, treatments, and choice tasks live in Subconscious, not here.** The ontology provides attributes, levels, archetypes, and context. Subconscious composes experiments.
3. **If a value is conditional on model, period, or experiment, it is an Estimate.**
4. **Every node has `schema_version`.** Every Estimate has `ontology_snapshot_hash`.
5. **Temporal validity (`valid_from`, `valid_to`) applies to AttributeLevel, RELEVANT_AT edges, Estimate, and Evidence.** Not to stable definitional nodes (Stage, Market scope, Transition definition).

## Pipeline

1. Research agent + executive interview extract node and edge candidates with evidence into JSONL.
2. Pydantic validates at the write boundary.
3. APOC imports validated JSONL into Neo4j.
4. Splink runs entity resolution on Offerings and StakeholderArchetypes after each ingestion pass.
5. Customer reviews the graph in Bloom.
6. Experiment context is projected to JSON (see `contracts/experiment_context.schema.json`) and sent to Subconscious.
7. Subconscious returns results (see `contracts/experiment_results.schema.json`) which land as Estimate nodes.

## What changed from v0

See `MIGRATION.md`.

## What's cut and why

See `v2_spec.md`.
