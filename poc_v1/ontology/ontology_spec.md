# Ontology Spec — v1 POC

## Purpose

Minimal, queryable context store for:

1. Subconscious.ai discrete choice experiment spec generation.
2. Wiki-style research agent ingestion with provenance.
3. Customer-facing visualization in Neo4j Bloom.

## Objects

### Market
Scope boundary. Every query is market-scoped. One market per ontology in v1. Context factors (budget state, regulatory pressure, urgency, channel) live here as JSONB-style properties in v1 and become first-class `ContextFactor` nodes in v2.

### Stage
AARRR stages as first-class nodes. Enables clean `FROM` / `TO` edges on transitions and lets the experiment designer query "which attributes matter at stage X."

### Transition
The state change being modeled (e.g., Consider → Choose). Holds no probabilities. All quantitative findings about a transition are Estimate nodes pointing at it.

### StakeholderArchetype
Who moves through stages. Distinguished as `customer`, `competitor_buyer`, or `competitor_user` via `archetype_type`. The `traits` dict remains as a backwards-compatible cache; the canonical persona-trait graph is `StakeholderArchetype -[:HAS_TRAIT]-> Trait -[:HAS_LEVEL]-> TraitLevel`.

**No sensitivities as properties.** Price/brand/trust sensitivities are posterior quantities from choice models. They land as Estimate nodes with `ABOUT` edges to the archetype.

### Offering
The object of study. `company_name` is a string prop in v1 with Splink dedupe; `Organization` becomes a node in v2.

### Attribute
A dimension of an Offering that can be varied in a DCE. Typically populated by Subconscious's API or by the research agent.

### AttributeLevel
Plausible levels for an Attribute in a Market for a time window. Temporally valid.

### Trait
A dimension of a StakeholderArchetype used to describe a persona.

### TraitLevel
Plausible levels for a Trait in a Market for a time window. Temporally valid.

### Evidence
Grounding for any node or edge. Required for every extracted fact per the ingestion rules.

### Estimate
Results returned from Subconscious. Every Estimate carries `ontology_snapshot_hash` so results are always interpretable against the ontology state they were computed on.

## Edges

| Edge | From | To | Notes |
|---|---|---|---|
| FROM | Transition | Stage | |
| TO | Transition | Stage | |
| IN_MARKET | Transition | Market | |
| RELEVANT_TO | Transition | StakeholderArchetype | Which archetypes participate in this transition |
| ABOUT | Transition OR Estimate | * | Polymorphic |
| HAS_ATTRIBUTE | Offering | Attribute | |
| HAS_LEVEL | Attribute OR Trait | AttributeLevel OR TraitLevel | |
| HAS_TRAIT | StakeholderArchetype | Trait | |
| RELEVANT_AT | Attribute | Stage | `{score, valid_from, valid_to, evidence_ids}` — temporal relevance |
| SUPPORTS | Evidence | * | Polymorphic |

## Design boundaries (what stays out)

- No probabilities on ontology nodes.
- No choice sets, alternatives, or experiment designs — those live in Subconscious.
- No metric formulas as prose — deferred to v2.
- No treatments on nodes — Subconscious owns treatments.
- No separate ContextFactor nodes in v1 — folded into props.
- Company/Product/Persona are the primary Twenty projection surfaces. Product maps to `Offering`; Persona maps to `StakeholderArchetype`. See `twenty_projection.md`.

## Ingestion rules

1. Every node must have at least one `SUPPORTS` edge from Evidence, with the one exception of Stage (definitional).
2. Pydantic validation at the write boundary is mandatory. No raw Cypher writes from the research agent.
3. Splink entity resolution runs after each ingestion batch on Offerings and StakeholderArchetypes.
4. Every write includes `schema_version`.
5. Estimates always include `ontology_snapshot_hash` computed from the subgraph Subconscious consumed.

## Temporal conventions

Temporal validity (`valid_from`, `valid_to`) applies to:
- `AttributeLevel` (levels shift as markets evolve)
- `TraitLevel` (levels shift as markets evolve)
- `RELEVANT_AT` edges (relevance of an attribute at a stage shifts over time)
- `Estimate` (each has a validity window matching the experiment period)
- `Evidence` (`period_observed`)

Does NOT apply to definitional nodes: `Stage`, `Market` scope, `Transition` definition, `Attribute` definition.

## Query patterns the ontology must serve fast

1. "Given Transition X in Market Y at period T, what Attributes are relevant at the to-Stage, with levels, with evidence?"
2. "Given Transition X, which StakeholderArchetypes participate?"
3. "Show all Estimates produced by Experiment E, with their ontology snapshot."
4. "Show all Evidence supporting AttributeLevel L."

All four should be 3-hop or fewer Cypher queries.
