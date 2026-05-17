# Market Simulation Ontology - v1 POC

## Purpose

This package is the minimal ontology that sits between:

- A wiki-style market research agent plus executive interview input
- The Subconscious.ai discrete choice experiment engine

The ontology is context for the experiment, not the experiment itself.
Subconscious owns experiment design and causal estimation. This repo owns the
structured context that feeds Subconscious and the structured results that come
back.

## Scope

Single customer, single company, 12-month horizon. POC-grade. See
`poc_v1/v2_spec.md` for the parking lot of things deliberately cut.

## Core model

Stakeholder archetypes plus persona traits, Offering attributes and levels, and
Market/Transition context go into Subconscious experiments. W&B/SuperEgo run
outputs come back as normalized `Estimate` nodes linked to the same ontology IDs
through `ExperimentRun` lineage.

## Stack

- FalkorDB-compatible property graph as the store.
- Pydantic at the write boundary for schema enforcement.
- Splink as a separate job for entity resolution on Offerings and StakeholderArchetypes.
- Deployment-specific import/export over validated JSONL fixtures.
- Postgres + pgvector as optional separate retrieval infrastructure for Evidence excerpts.

## Node Types

The authoritative count is `len(NODE_MODELS)` in
`poc_v1/ontology/schema.py`.

| Node | Purpose |
|---|---|
| Market | Scope boundary for every query |
| Stage | AARRR stage as a first-class node |
| Transition | The state change being modeled |
| StakeholderArchetype | Customer or competitor-side archetype |
| Offering | Object of study, such as product, service, or SKU |
| Attribute | Dimension of an Offering that can be varied |
| AttributeLevel | Plausible level for an Attribute in a Market/period |
| Trait | Dimension of a StakeholderArchetype used to describe a persona |
| TraitLevel | Plausible level for a Trait in a Market/period |
| Need | Outcome a StakeholderArchetype wants — the job-to-be-done behind a Transition |
| Evidence | Source grounding for any node |
| Estimate | Part-worth, AMCE, importance, or other returned quantity |
| Company | Organization that offers one or more Offerings |
| ExperimentRun | Execution record tying an ontology snapshot to SuperEgo/W&B artifacts |

## Edge Types

The authoritative count is `len(EDGE_MODELS)` in
`poc_v1/ontology/schema.py`.

```text
Transition -[:FROM]-> Stage
Transition -[:TO]-> Stage
Transition -[:IN_MARKET]-> Market
Transition -[:RELEVANT_TO]-> StakeholderArchetype
Transition -[:ABOUT]-> Offering
Offering -[:HAS_ATTRIBUTE]-> Attribute
Offering -[:OFFERED_BY]-> Company
Attribute -[:HAS_LEVEL]-> AttributeLevel
Trait -[:HAS_LEVEL]-> TraitLevel
StakeholderArchetype -[:HAS_TRAIT]-> Trait
Attribute -[:RELEVANT_AT {score, valid_from, valid_to, evidence_ids}]-> Stage
Attribute -[:ADDRESSES]-> Need
StakeholderArchetype -[:HAS_NEED]-> Need
Evidence -[:SUPPORTS]-> *
Estimate -[:ABOUT]-> *
ExperimentRun -[:CONSUMED]-> *
ExperimentRun -[:PRODUCED]-> Estimate
```

## Golden Rules

1. No probabilities or part-worths on ontology nodes. Those are `Estimate`s.
2. Causal DAGs are projection artifacts over ontology IDs, not ontology edges.
3. W&B stores experiment provenance and artifacts; the ontology stores stable IDs, lineage, and normalized estimates.
4. Dependent variables, persona traits/levels, and attribute treatments/levels must enter experiments from ontology IDs.
5. Run-local W&B/SuperEgo IDs must map back to ontology IDs through a versioned mapping artifact.

## Public modules (consumer imports)

Three sibling modules, all under `poc_v1.ontology`, are the public API
that downstream consumers (spice-harvester, burn-substrate Graphiti
sidecar, twenty CRM, future research agents) import directly:

```python
from poc_v1.ontology.schema import (
    NODE_MODELS, EDGE_MODELS, SCHEMA_VERSION,
)
from poc_v1.ontology.graphiti_views import (
    ENTITY_TYPES,    # graphiti-compatible Pydantic view of NODE_MODELS
    EDGE_TYPES,      # graphiti-compatible Pydantic view of EDGE_MODELS
    EDGE_TYPE_MAP,   # dict[(src_label, tgt_label), list[predicate]]
)
from poc_v1.ontology.identity import (
    CompanyIdentity, # dataclass(canonical_domain, route_slug, group_id)
    to_identity,     # email/URL/domain/slug → identity (PSL-aware)
    normalize_slug,  # boundary validator for HTTP routes (no PSL)
)
from poc_v1.ontology.iri import (
    to_iri,        # (class_name, node_id) -> stable entity IRI
    class_iri,     # class name -> stable RDF class IRI
    parse_iri,     # entity IRI -> (class_name, node_id)
    predicate_iri, # edge label -> stable predicate IRI
)
```

Single source of truth — adding a new node/edge to `schema.py`
automatically propagates to `graphiti_views`. Identity shape (the trio
`canonical_domain` / `route_slug` / `group_id`) is part of "what
defines a Company" so it lives next to the Pydantic Company model.
IRI shape is also centralized here so RDF/TrustGraph projections use one
dereferenceable namespace: `https://ontology.subconscious.ai`.

## Pipeline

1. Research agent and executive interview extract node and edge candidates with evidence into JSONL.
2. Pydantic validates the ontology write boundary.
3. The graph-store adapter imports validated JSONL into a FalkorDB-compatible property graph.
4. Experiment context is projected from ontology IDs into SuperEgo/W&B contracts.
5. SuperEgo/W&B run-local IDs are bound back to ontology IDs through `poc_v1/contracts/experiment_run_mapping.schema.json`.
6. Normalized results from W&B artifacts become `Estimate` nodes and `ABOUT`/`PRODUCED` edges.
7. Recommendations remain artifacts until promoted by a human or a later graph-native claim model.

## See Also

- `CLAUDE.md` - agent guidance
- `AGENTS.md` - Codex harness pointer
- `poc_v1/MIGRATION.md` - what changed from v0
- `poc_v1/v2_spec.md` - what is deliberately cut from v1
