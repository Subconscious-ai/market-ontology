# Causal Projection Library Grounding

This repo owns ontology contracts and lightweight validators. It does not own
causal estimation runtimes.

## Dependency Posture

- Runtime schema dependency: `pydantic>=2`.
- CI/dev validation dependencies: `jsonschema[format]>=4`, `networkx>=3`.
- Integration targets, not core dependencies: CausalNex, EconML, CausalFlow,
  RDFLib, W&B.

Do not make downstream users install heavy causal libraries just to validate KG
writes. Encode their required semantics in artifacts and keep runtime adapters
outside the core schema path unless a consumer needs them.

## Non-Negotiables

- The ontology is a typed property graph, not a causal DAG.
- Causal DAG edges live only in `causal_dag_projection` artifacts.
- Ontology IDs are the stable join surface across graph, experiments, W&B, and
  recommendations.
- `ExperimentRun` records lineage. It does not assert causal truth.
- `Estimate` records quantitative outputs against an `ontology_snapshot_hash`.
- Recommendations remain artifacts, not graph truth.

## NetworkX

Use NetworkX for validation and deterministic adapter output.

- Node IDs are projection `variable_id` values.
- Node attributes carry `ontology_node_type`, `ontology_node_id`,
  `estimator_role`, `value_type`, `observed_column`, and optional `state_space`.
- Edge attributes carry `edge_source`, `lag`, `rationale`, and `evidence_ids`.
- Validate endpoints before calling `DiGraph.add_edge`; NetworkX can create
  missing endpoint nodes implicitly.
- Validate acyclicity and emit `topological_order`.

## CausalNex

CausalNex consumes DAG structures over random variables.

- Use projection variables as random variables, not ontology nodes directly.
- `state_space` is required when using discrete Bayesian-network workflows.
- Discretization assumptions belong in `assumptions`.
- Human review remains required before turning learned structure into causal
  claims.

## EconML

EconML estimators need estimator semantics, not generic graph labels.

- `estimator_role: "Y"` marks the outcome.
- `estimator_role: "T"` marks treatments.
- `estimator_role: "X"` marks effect modifiers/covariates.
- `estimator_role: "W"` marks controls/confounders.
- `observed_column` is the bridge from ontology variable to analysis matrix.
- `estimation_target` is mandatory so different estimators cannot reinterpret
  the same projection differently.

## CausalFlow

Use CausalFlow-style projections only when time-series data exists.

- Set `time_series.enabled: true`.
- Provide `time_index_column`, `min_lag`, `max_lag`, and preferably
  `panel_id_column`.
- Every causal edge must have `lag`.
- Same-time feedback loops should be represented as lagged edges or rejected.

## RDF 1.1 And RDFLib

RDF is not a property graph serialization by default. It needs an explicit
mapping.

- Map ontology IDs and projection IDs to IRIs.
- Use RDF triples for ontology facts and projection metadata.
- Use a named graph or dataset context for `ontology_snapshot_hash`.
- Do not equate FalkorDB JSONL records with RDF triples without a mapper.

## W&B

W&B artifact aliases are useful labels but mutable.

- Store immutable artifact identity fields: `entity`, `project`, `name`,
  `type`, `version`, and `digest`.
- Store aliases as observed metadata, never as the primary identity.
- Do not claim a digest is real unless it was read from W&B.

## FalkorDB

FalkorDB is the property-graph store.

- Store ontology context and run lineage in the graph.
- Keep causal assumptions in projection artifacts.
- If an importer cannot store nested `wandb_artifacts`, serialize them in the
  adapter layer rather than weakening the ontology contract.

## Sources

- NetworkX DiGraph: https://networkx.org/documentation/stable/reference/classes/digraph.html
- CausalNex guide: https://causalnex.readthedocs.io/en/latest/04_user_guide/04_user_guide.html
- EconML DML: https://www.pywhy.org/EconML/_autosummary/econml.dml.DML.html
- EconML DML guide: https://www.pywhy.org/EconML/spec/estimation/dml.html
- CausalFlow: https://lcastri.github.io/causalflow/causal_discovery/
- RDF 1.1 Concepts: https://www.w3.org/TR/rdf11-concepts/
- RDFLib graphs: https://rdflib.readthedocs.io/en/7.1.4/intro_to_graphs.html
- W&B Artifact: https://docs.wandb.ai/models/ref/python/experiments/artifact
- FalkorDB docs: https://docs.falkordb.com/
- JSON Schema 2020-12 validation: https://json-schema.org/draft/2020-12/json-schema-validation
