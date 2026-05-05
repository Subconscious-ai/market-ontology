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
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json
python -m unittest discover -s tests -v
bash scripts/check-doc-rot.sh
python -m py_compile poc_v1/ontology/schema.py
```

If any fail, fix before opening a PR. Do not use `--no-verify`.

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
projection artifacts.

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
    schema.py
    node_schemas.json
    edge_schemas.json
    kg_seed_contract.json
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
scripts/
  validate_kg_seed.py
  validate_causal_dag.py
  validate_causal_projection.py
  generate_kg_seed_contract.py
  generate_twenty_app.py
tests/
```

## Golden Rules

1. No probabilities or part-worths on ontology nodes. Those are `Estimate`s.
2. The ontology is not a causal DAG. DAGs are validated artifacts over ontology IDs.
3. W&B is experiment provenance, not ontology truth.
4. Every new fixture file must appear in `scripts/validate_kg_seed.py::FIXTURES`.
5. Breaking schema changes require coordination with downstream writers/readers.

## Conventions

- Branches normally use `codex/<short-slug>` for Codex work.
- Keep PRs focused: schema change plus fixture plus validator tests is one PR.
- Do not delete or rewrite user work to clean the tree; preserve it first.
