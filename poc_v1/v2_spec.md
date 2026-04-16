# v2 Parking Lot

Everything we deliberately cut from v1 to ship faster. Each item has a **triggering condition** — when you hit it, revisit.

## Node types deferred

### `Trait` as a first-class node

**Current (v1):** Traits live inside `StakeholderArchetype.traits` as a JSONB dict.

**Proposed (v2):** `Trait` node with edges `StakeholderArchetype -[:HAS_TRAIT]-> Trait`.

**Why defer:** For a single-company POC with ~5-20 archetypes, JSONB is sufficient and far simpler.

**Triggering condition:** Any of the following —
- You have >50 archetypes and traits are getting duplicated.
- You want to query "all archetypes with trait X across markets."
- You need evidence attached to specific traits, not just to the archetype as a whole.
- Customers ask for trait-level heterogeneity in part-worths.

---

### `ContextFactor` and `ContextFactorValue` as nodes

**Current (v1):** Context factors live inside `Market.context_factors` as a JSONB dict.

**Proposed (v2):** `ContextFactor` node with allowed values, `ContextFactorValue` instantiating it per Market/period with temporal validity, `MODERATES` edges to transitions.

**Why defer:** For one market in v1, JSONB is fine.

**Triggering condition:**
- You have >3 markets and context factors are diverging.
- You want to query "which transitions does regulatory pressure moderate, across markets?"
- Context factors need their own evidence trail.
- JSONB search on `context_factors` becomes a bottleneck.

---

### `Organization` as a first-class node

**Current (v1):** `Offering.company_name` is a string property with Splink dedupe.

**Proposed (v2):** `Organization` node with `canonical_name`, `aliases[]`, `domain`, `ticker`, etc. `Offering -[:OFFERED_BY]-> Organization`.

**Why defer:** Splink handles the entity resolution well enough for ~50-200 offerings.

**Triggering condition:**
- Competitor analysis becomes a first-class deliverable.
- You need to track M&A, rebrandings, parent/child corporate structure.
- One organization sells multiple offerings and you need to query across them.
- You want to attach evidence to companies, not just offerings.

---

### `Metric` as a node with formula DSL

**Current (v1):** No Metric node. Part-worths and WTP are Estimate nodes directly.

**Proposed (v2):** `Metric` node with executable `formula_dsl` (not prose), `MOVES` edges from transitions.

**Why defer:** Customers care about part-worths at POC stage, not KPI dashboards.

**Triggering condition:**
- Customer asks for rollup KPIs across experiments ("total revenue impact of provenance visibility investment").
- You want automated recomputation of metrics when Estimates change.
- Multiple experiments contribute to one metric and need aggregation.

---

### `Experiment` as a node

**Current (v1):** `subconscious_experiment_id` is a string on every Estimate.

**Proposed (v2):** `Experiment` node with research question, design metadata, and `PRODUCES` edges to Estimates.

**Why defer:** For 1-2 experiments per month at POC scale, the string ID is fine.

**Triggering condition:**
- You run >10 experiments and need to query experiment metadata.
- One experiment produces hundreds of estimates and you need fast "show all estimates from experiment X" with rich filtering.
- Experiment design metadata becomes customer-facing.

---

## Edge types deferred

### `Evidence -[:CONTRADICTS]-> Evidence`

**Why defer:** Wiki-style UI doesn't need to display contradictions in v1.

**Triggering condition:** Customers report confusion when the research agent extracts conflicting claims. The wiki needs to show "here's the claim, here are sources that agree, here are sources that disagree."

---

### `Evidence -[:SUPERSEDES]-> Evidence`

**Why defer:** In v1, supersession is tracked by `valid_to` on the superseded evidence. Good enough.

**Triggering condition:** Customers need explicit "this updated claim replaced that earlier claim" chains for audit defensibility.

---

### `StakeholderArchetype -[:ACTIVE_IN]-> Market` and `-[:AT_STAGE]-> Stage`

**Why defer:** In v1, archetype-market-stage association is inferred via transitions (`Transition -[:IN_MARKET]-> Market` + `Transition -[:RELEVANT_TO]-> Archetype`).

**Triggering condition:** You want to query "which archetypes exist in market X at stage Y" without going through a specific transition. Common enough at scale to justify the direct edges.

---

### `Attribute -[:MODERATED_BY]-> ContextFactor`

Only becomes meaningful after `ContextFactor` is promoted to a node.

---

## Property deferrals

### Temporal validity on more nodes

Currently: AttributeLevel, Estimate, Evidence, RELEVANT_AT edges.

**Triggering condition for expansion:**
- Offerings change category/positioning over time → add temporal validity to Offering.
- Archetypes shift meaningfully year-over-year → add temporal validity to StakeholderArchetype.
- Market definitions evolve → add temporal validity to Market.

### Bitemporal (valid-time + transaction-time)

**Current:** Valid-time only via `valid_from`/`valid_to`.

**Proposed (v2):** Also track `recorded_at` / `recorded_to` for "what did we know when." This is what Graphiti gives you natively.

**Triggering condition:**
- Auditability for regulated customers.
- Need to reproduce "what did our knowledge graph look like on date X" for retrospective analysis.
- Research agent updates the same facts frequently and you need to track belief revision.

---

## Tooling deferrals

### Graphiti for ingestion

**Why defer:** Adds operational complexity; Pydantic + Splink covers v1 needs.

**Triggering condition:**
- Research agent ingestion quality plateaus with current stack.
- You need episodic/conversational memory semantics over document streams.
- Entity resolution via Splink becomes insufficient.
- Bitemporal tracking becomes a requirement.

### Multi-tenancy

**Current:** One ontology per customer, one customer per deployment.

**Proposed (v2):** Neo4j database-per-tenant or strict labeling for multi-tenant isolation.

**Triggering condition:** You take on a second customer. This is not optional — plan for it before signing the second deal.

### Postgres + pg_vector as secondary store

**Why defer:** Not needed if the research agent doesn't do heavy semantic retrieval over Evidence.

**Triggering condition:** The research agent needs vector search over Evidence excerpts or extracted claims. At that point, stand up Postgres alongside Neo4j and sync Evidence to it.

### TerminusDB or Stardog instead of Neo4j

**Why defer:** Neo4j + Bloom covers current needs. Switching costs are high.

**Triggering condition:**
- You need OWL reasoning (subsumption, consistency checking).
- Schema versioning with git-like branching becomes essential (TerminusDB's niche).
- Enterprise customer requires RDF/SPARQL interop.

---

## How to use this document

When you hit a triggering condition, open this doc, find the item, and spec out the migration. Add a MIGRATION-v2.md entry just like MIGRATION.md. Version the schema (1.1.0, 1.2.0, etc.). Don't bundle multiple v2 items into one release unless they're genuinely coupled.

## One rule

**Resist the urge to pre-build v2 items before triggering conditions are met.** Every deferred node type is an unshipped feature that also an unpaid operational cost. Ship, measure, then promote.
