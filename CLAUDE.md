# CLAUDE.md

This file provides guidance to agents working in this repository.

## Repository Overview

`market-ontology` is the canonical Pydantic schema enforcer for the
Subconscious knowledge graph. It sits between research/interview ingestion and
the Subconscious.ai experiment engine.

The ontology is context for experiments, not the experiment itself. Dependent
variables, persona traits/levels, and offering attribute treatments/levels are
projected from ontology IDs into SuperEgo/W&B. W&B outputs return as immutable
artifact lineage plus normalized `Estimate` nodes linked back to those ontology
IDs.

## Setup

One-time, in a venv at the repo root:

```bash
pip install -e ".[dev]"
```

This installs `market-ontology` and dev validation dependencies. The package
version is read from `SCHEMA_VERSION` in `poc_v1/ontology/schema.py`.

## Commands

```bash
python scripts/validate_causal_dag.py
python -m unittest tests.test_causal_dag_v1 -v
python scripts/validate_kg_seed.py
python scripts/generate_kg_seed_contract.py --check
python scripts/generate_twenty_app.py --check
python scripts/generate_trustgraph_ontology.py --check
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json
python -m unittest discover -s tests -v
bash scripts/check-doc-rot.sh
python -m py_compile poc_v1/ontology/schema.py
```

If any fail, fix before opening a PR. Do not use `--no-verify`.

`main` is gated by two GitHub Actions workflows: `ci.yml` runs the full
sequence above; `symphony-gate.yml` runs the `scripts/agent/` harness
(`readiness.sh`, `preflight.sh`, `validate-fast.sh`). Python 3.11 is the
CI baseline (`requires-python >= 3.11`) — do not rely on 3.12+-only syntax.

## Symphony Contract

- Task types: `schema-contract`, `ontology-fixture`, `docs-canary`, `ci-harness`, `consumer-contract`.
- Allowed surfaces: `poc_v1/ontology/`, `poc_v1/contracts/`, `scripts/`, `tests/`, `docs/`, `README.md`, and `scripts/agent/`.
- Forbidden unless explicit: incompatible schema migrations, downstream app rewrites, generated contract churn without source change, secrets, production env, and unrelated cleanup.
- Fast gate: `bash scripts/agent/validate-fast.sh`; keep it schema/unit/doc focused. Use `validate-full.sh` for broader consumer or integration checks.

## Architecture

`poc_v1/ontology/schema.py` defines Pydantic models, `NODE_MODELS`,
`EDGE_MODELS`, and `SCHEMA_VERSION`. It is the only source of truth for graph
shape. Generated JSON files under `poc_v1/ontology/` must be regenerated from
the schema and not hand-edited.

Current graph additions for experiment lineage are intentionally small:

- Node: `ExperimentRun`
- Edges: `CONSUMED`, `PRODUCED`

Do not add raw causal graph edges such as `CAUSES`, `AFFECTS`,
`HAS_TREATMENT`, or `HAS_OUTCOME` to the ontology. Causal assumptions live in
projection artifacts and in the `causal_dag_v1/` peer module (below).

### `causal_dag_v1/` — the causal peer module

`poc_v1` is a labeled property graph of *types* whose edges express
structure (`HAS_ATTRIBUTE`, `FROM`, `TO`). It is deliberately not a causal
DAG. `causal_dag_v1/` is the peer module that holds the *causal* layer:
nodes (`Cause`, `Effect`, `Mediator`, `Moderator`, `Confounder`,
`Intervention`) and edges (`CAUSES` with direction/sign/effect_size/CI,
`MEDIATES`, `MODERATES`, `CONFOUNDED_BY`). It has its own Pydantic models
(`causal_dag_v1/nodes.py`, `edges.py`) and acyclicity validation
(`validate.py`, NetworkX-backed). `scripts/validate_causal_dag.py` reads
`causal_dag_v1/kg_seed/*.jsonl` and gates it in CI. Ontology (`poc_v1`) is
*context*; causal hypotheses (`causal_dag_v1`) are *result* — keep them
separate.

### Public modules (consumer imports)

The schema repo also hosts three derived modules that every downstream
consumer (spice-harvester, burn-substrate Graphiti sidecar, twenty CRM,
future research agents) imports directly. Keeping them next to
`schema.py` means consumers can't drift away from the canonical shape.

```python
from poc_v1.ontology.schema import (
    NODE_MODELS, EDGE_MODELS, SCHEMA_VERSION,
)
from poc_v1.ontology.graphiti_views import (
    ENTITY_TYPES,    # dict[str, type[BaseModel]]  — graphiti-compatible view
    EDGE_TYPES,      # dict[str, type[BaseModel]]  — graphiti-compatible view
    EDGE_TYPE_MAP,   # dict[(src, tgt), list[str]] — what add_episode wants
)
from poc_v1.ontology.identity import (
    CompanyIdentity, # dataclass(canonical_domain, route_slug, group_id)
    to_identity,     # email/URL/domain/slug → identity
    email_to_slug,
    domain_to_slug,
    normalize_slug,  # boundary validator (HTTP routes; subset of to_identity)
)
from poc_v1.ontology.iri import (
    BASE_NAMESPACE,  # the single namespace every ontology IRI lives under
    to_iri,          # (class, id) → node IRI;   parse_iri  is its inverse
    class_iri,       # class → class (type) IRI
    predicate_iri,   # edge name → predicate IRI; parse_predicate_iri inverse
    property_iri,    # field name → property IRI; parse_property_iri inverse
)
```

`graphiti_views` derives ENTITY_TYPES/EDGE_TYPES from NODE_MODELS/EDGE_MODELS
by stripping graphiti-reserved fields (`uuid`, `name`, `summary`, …) and
`Any`-typed fields (which OpenAI structured outputs reject). EDGE_TYPE_MAP
is a cartesian product over `kg_seed_contract.json::edges`. Adding a
new node/edge to schema.py automatically propagates — no consumer-side
code change needed.

`identity` is the TLD-preserving, PSL-aware company resolver
(tldextract-backed). `person@ibm.com` and `person@ibm.ai` resolve to
distinct group_ids (`spice_ibm_com` vs `spice_ibm_ai`); subdomains
collapse to the brand (`mail.acme.io` → `acme_io`). IDN punycodes,
multi-part TLDs (`lloyds.co.uk` → `lloyds_co_uk`) work out of the box.

`iri` mints the canonical RDF IRI for every ontology node instance,
class, edge predicate, and literal property — four disjoint namespaces
under `https://ontology.subconscious.ai` (`/<Class>/<id>`, `/class/…`,
`/predicate/…`, `/property/…`). It is a schema-decoupled boundary
serializer: every `to_*`/`parse_*` pair round-trips exactly, ids are
percent-encoded so a `/` can't leak a path segment, and IRIs are
instance-stable — they do not encode `SCHEMA_VERSION`. Consumed by the
TrustGraph projection layer and spice-harvester `typed_graph` emission.

## W&B/SuperEgo Loop

The loop is:

1. Ontology snapshot projects experiment inputs:
   `Transition`, `StakeholderArchetype`, `Trait`, `TraitLevel`, `Attribute`,
   and `AttributeLevel`.
2. SuperEgo/W&B run-local IDs are written into
   `poc_v1/contracts/experiment_run_mapping.schema.json`.
3. W&B artifacts provide immutable provenance: entity, project, run id, artifact
   name, type, version, digest, and file metadata. Aliases such as `latest` are
   metadata only.
4. Normalized AMCE/WTP/importance results become `Estimate` nodes and
   `ABOUT`/`PRODUCED` edges.

## Directory Layout

```text
poc_v1/
  ontology/
    schema.py                # canonical Pydantic models + NODE/EDGE_MODELS
    graphiti_views.py        # typed view for Graphiti.add_episode (consumer import)
    identity.py              # company-identity resolver (consumer import)
    node_schemas.json        # generated; do not hand-edit
    edge_schemas.json        # generated; do not hand-edit
    kg_seed_contract.json    # generated by scripts/generate_kg_seed_contract.py
    twenty_projection.json
    twenty_app_contract.json
    super_ego_projection.json
  kg_seed/
    *.jsonl
  contracts/
    experiment_context.schema.json
    experiment_results.schema.json
    causal_dag_projection.schema.json
    experiment_run_mapping.schema.json
    normalized_experiment_results.schema.json
    market_signal.schema.json
    recommendation.schema.json
  adapters/
    legacy graph-store adapters
causal_dag_v1/                 # causal peer module (see Architecture)
  nodes.py edges.py validate.py
  kg_seed/*.jsonl
scripts/
  validate_kg_seed.py
  validate_causal_dag.py
  validate_causal_projection.py
  check_accepted_state_spine.py # gates the accepted-state spine contract
  generate_kg_seed_contract.py
  generate_twenty_app.py
  check-doc-rot.sh              # keeps CLAUDE.md/READMEs honest vs the code
  agent/                        # validate-fast.sh / validate-full.sh + helpers
tests/
```

The single fast gate is `bash scripts/agent/validate-fast.sh` — it runs
every command in the Commands section plus the generators in `--check`
mode. Run it before opening a PR rather than each command by hand.

## Golden Rules

1. No probabilities or part-worths on ontology nodes. Those are `Estimate`s.
2. The ontology is not a causal DAG. DAGs are validated artifacts over ontology IDs.
3. W&B is experiment provenance, not ontology truth.
4. Every new fixture file must appear in `scripts/validate_kg_seed.py::FIXTURES`.
5. Breaking schema changes require coordination with downstream writers/readers.

## Conventions

- Branches normally use `codex/<issue-id>-<short-slug>` for Codex work so
  PRs can be traced back to their driving issue.
- Keep PRs focused: schema change plus fixture plus validator tests is one PR.
- Do not delete or rewrite user work to clean the tree; preserve it first.
