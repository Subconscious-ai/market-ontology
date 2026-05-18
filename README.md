# market-ontology

Canonical Pydantic schema for the Subconscious knowledge graph. It sits between
research / interview ingestion and the Subconscious.ai discrete-choice
experiment engine.

The ontology is **context for experiments, not the experiment itself.** This
repo owns the structured context fed to Subconscious and the normalized results
that come back. Subconscious owns experiment design and causal estimation.

## Install

```bash
pip install -e ".[dev]"
```

Installs `market-ontology` plus dev validation dependencies. The package version
tracks `SCHEMA_VERSION` in `poc_v1/ontology/schema.py`.

## The public contract

Downstream consumers (spice-harvester, ai-chatbot-native-sizzle, twenty CRM,
burn-substrate Graphiti sidecar) import these four modules directly:

```python
from poc_v1.ontology.schema         import NODE_MODELS, EDGE_MODELS, SCHEMA_VERSION
from poc_v1.ontology.graphiti_views import ENTITY_TYPES, EDGE_TYPES, EDGE_TYPE_MAP
from poc_v1.ontology.identity       import CompanyIdentity, to_identity, normalize_slug
from poc_v1.ontology.iri            import BASE_NAMESPACE, to_iri, class_iri, predicate_iri, property_iri
```

`schema.py` is the single source of truth for graph shape. `graphiti_views` and
every generated `*.json` / `*.ttl` artifact under `poc_v1/ontology/` derive from
it — never hand-edited. For the authoritative node and edge counts, read
`len(NODE_MODELS)` / `len(EDGE_MODELS)`; the full typed spec is in
`ontology_spec.md` (linked below).

## Where to look

| You want… | Read |
|---|---|
| To work in this repo — agents and contributors | `CLAUDE.md` |
| The full node / edge / temporal spec | `poc_v1/ontology/ontology_spec.md` |
| A visual map of the repo and its consumers | `docs/architecture.html` |
| Why a structural decision was made | `docs/adr/` |
| What changed between schema versions | `poc_v1/MIGRATION.md` |
| What was deliberately cut from v1 | `poc_v1/v2_spec.md` |
| The causal layer (a peer module, not the ontology) | `causal_dag_v1/` |

## Golden rules

1. No probabilities or part-worths on ontology nodes — those are `Estimate` nodes.
2. The ontology is not a causal DAG. Causal hypotheses live in `causal_dag_v1/`
   and in projection artifacts over ontology IDs.
3. W&B is experiment provenance, not ontology truth.
4. Every new kg_seed fixture must be registered in
   `scripts/validate_kg_seed.py::FIXTURES`.
5. Breaking schema changes require coordinating downstream consumers in the same
   PR round.

Full guidance, commands, and the schema-change recipe live in **`CLAUDE.md`** —
start there.
