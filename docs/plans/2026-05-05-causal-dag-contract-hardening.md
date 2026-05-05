# Causal DAG Contract Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the causal projection contracts reproducible enough for NetworkX validation, CausalNex structure review, EconML estimation, CausalFlow time-series discovery, RDF/RDFLib export, W&B lineage, and FalkorDB-backed ontology traceability without adding causal edges to the ontology.

**Architecture:** Keep the market ontology as the source of truth and keep causal DAGs as versioned projection artifacts over ontology IDs. Add strict artifact validation, optional library adapters, and immutable run lineage. Do not add graph-native `CAUSES` or new causal node types.

**Tech Stack:** Pydantic schema models, JSON Schema 2020-12 contracts, `jsonschema` for CI contract validation, NetworkX for DAG validation/topological order in tooling, FalkorDB property graph semantics, W&B artifact identity fields, and library-neutral projection fields for CausalNex, EconML, CausalFlow, and RDFLib.

---

## Decision-Relevant Objection

The current repo is not actually using NetworkX, EconML, CausalNex, CausalFlow, RDFLib, or W&B as installed dependencies. Local import checks show those packages are absent except `jsonschema`. Treating them as hard runtime dependencies in `market-ontology` would be a mistake.

Implementation posture:
- Add `jsonschema` and NetworkX as CI/dev validation dependencies only.
- Do not add EconML, CausalNex, CausalFlow, RDFLib, or W&B as runtime dependencies in this schema repo.
- Encode the stable contract fields those tools need.
- Add optional adapter/export code only where it does not force heavy downstream libraries into this repo.

Confidence: high for local dependency status; high for keeping the ontology and causal projections separate; moderate for exact SuperEgo/W&B field names until live artifacts are inspected.

## Library Grounding

- NetworkX `DiGraph` supports node/edge attributes, but `add_edge` adds missing endpoint nodes automatically. Validator must check endpoints before graph construction.
- CausalNex uses DAG structure over variables plus review and CPD/likelihood estimation. The projection must identify random variables and, when used for Bayesian networks, discrete state spaces or discretization assumptions.
- EconML DML-style estimators require unambiguous `Y`, `T`, `X`, and `W` semantics: outcome, treatment, effect modifiers/covariates, and controls/confounders.
- CausalFlow targets time-series causal discovery and exposes lag parameters such as `min_lag` and `max_lag`. A static causal edge is not enough for market-news-driven updates.
- RDF/RDFLib represent graphs as triples, and RDF datasets can use named graphs. RDF export should map ontology IDs and projection IDs to IRIs rather than pretending property-graph JSON is RDF.
- W&B artifacts have mutable aliases and immutable identity/versioning fields such as version and digest. The KG should record immutable identity, not only display names or aliases.
- FalkorDB is a property graph with OpenCypher traversal. The KG should answer lineage queries; causal assumptions stay in artifacts.
- JSON Schema `format` is not guaranteed to assert validity unless the validator enables format assertions or explicit format checking.

Primary docs:
- NetworkX DiGraph: https://networkx.org/documentation/stable/reference/classes/digraph.html
- CausalNex guide: https://causalnex.readthedocs.io/en/latest/04_user_guide/04_user_guide.html
- EconML DML: https://www.pywhy.org/EconML/_autosummary/econml.dml.DML.html
- EconML DML guide: https://www.pywhy.org/EconML/spec/estimation/dml.html
- CausalFlow: https://lcastri.github.io/causalflow/causal_discovery/
- RDF 1.1: https://www.w3.org/TR/rdf-concepts/
- RDFLib graphs: https://rdflib.readthedocs.io/en/6.3.1/intro_to_graphs.html
- W&B Artifact: https://docs.wandb.ai/models/ref/python/experiments/artifact
- FalkorDB docs: https://docs.falkordb.com/
- JSON Schema 2020-12 validation: https://json-schema.org/draft/2020-12/json-schema-validation

---

### Task 1: Add Contract Validation Dependencies To CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`

**Step 1: Write the failing test expectation**

Update or add a test that imports:

```python
from jsonschema import Draft202012Validator, FormatChecker
```

Expected before CI change: local may pass, but CI would fail because only `pydantic>=2` is installed.

**Step 2: Update CI install command**

Change:

```bash
pip install 'pydantic>=2'
```

to:

```bash
pip install 'pydantic>=2' 'jsonschema[format]>=4' 'networkx>=3'
```

**Step 3: Document dependency posture**

Update agent docs to say:

```text
Runtime schema dependency: pydantic>=2.
CI/dev validation dependencies: jsonschema[format]>=4, networkx>=3.
EconML/CausalNex/CausalFlow/RDFLib/W&B are integration targets, not core repo runtime dependencies.
```

**Step 4: Run targeted verification**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: existing tests still pass after CI/docs changes.

---

### Task 2: Write Failing Tests For Strict Contract Validation

**Files:**
- Modify: `tests/test_causal_projection_contracts.py`
- Create: `tests/test_validate_causal_projection.py`

**Step 1: Test JSON Schema meta-validation**

Add tests using `Draft202012Validator.check_schema(contract)` for:
- `causal_dag_projection.schema.json`
- `experiment_run_mapping.schema.json`
- `normalized_experiment_results.schema.json`
- `market_signal.schema.json`
- `recommendation.schema.json`

**Step 2: Test `additionalProperties` rejection**

Use a valid sample object and inject:

```python
sample["not_in_contract"] = "should fail"
```

Expected: JSON Schema validation fails.

**Step 3: Test `format` rejection**

Use:

```python
sample["generated_at"] = "not-a-date"
```

Expected: JSON Schema validation fails with `FormatChecker`.

**Step 4: Test DAG semantic failures**

Create tests for `scripts.validate_causal_projection.validate_projection`:

```python
def test_rejects_unknown_edge_endpoint():
    projection["causal_edges"][0]["target_variable_id"] = "missing"
    errors = validate_projection(projection)
    assert "unknown target_variable_id" in errors[0]
```

```python
def test_rejects_cycle():
    projection["causal_edges"] = [
        {"source_variable_id": "a", "target_variable_id": "b"},
        {"source_variable_id": "b", "target_variable_id": "a"},
    ]
    errors = validate_projection(projection)
    assert "cycle" in errors[0].lower()
```

```python
def test_valid_projection_emits_topological_order():
    normalized = normalize_projection(projection)
    assert normalized["topological_order"] == ["treatment_provenance", "outcome_consider_choose"]
```

Expected before implementation: import failure or validation functions missing.

---

### Task 3: Harden `causal_dag_projection.schema.json`

**Files:**
- Modify: `poc_v1/contracts/causal_dag_projection.schema.json`
- Test: `tests/test_causal_projection_contracts.py`
- Test: `tests/test_validate_causal_projection.py`

**Step 1: Close all objects**

Add `additionalProperties: false` to:
- root object
- `outcome`
- `runtime`
- `$defs.ontology_ref`
- `$defs.ontology_variable`
- `$defs.causal_edge`
- new nested objects added below

**Step 2: Add deterministic graph fields**

Add root properties:

```json
"projection_id": {"type": "string"},
"topological_order": {
  "type": "array",
  "items": {"type": "string"}
}
```

Make `projection_id` required. Keep `topological_order` optional on input but required in normalized output from the validator.

**Step 3: Replace ambiguous variable roles with estimator semantics**

Keep `role` for human readability, but add required `estimator_role`:

```json
"estimator_role": {
  "type": "string",
  "enum": ["Y", "T", "X", "W", "context", "time_index", "panel_id"]
}
```

Add:

```json
"observed_column": {"type": ["string", "null"]},
"value_type": {
  "type": "string",
  "enum": ["binary", "categorical", "ordinal", "continuous", "text"]
},
"state_space": {
  "type": "array",
  "items": {"type": ["string", "number", "boolean"]}
}
```

Rationale:
- `Y/T/X/W` is the least ambiguous EconML-compatible split.
- `state_space` supports CausalNex/discrete Bayesian network usage.
- `observed_column` connects projection variables to result matrices without inventing graph nodes.

**Step 4: Add explicit outcome/treatment metadata**

Add root property:

```json
"estimation_target": {
  "type": "object",
  "required": ["outcome_variable_id", "treatment_variable_ids"],
  "additionalProperties": false,
  "properties": {
    "outcome_variable_id": {"type": "string"},
    "treatment_variable_ids": {"type": "array", "items": {"type": "string"}},
    "effect_modifier_variable_ids": {"type": "array", "items": {"type": "string"}},
    "control_variable_ids": {"type": "array", "items": {"type": "string"}}
  }
}
```

Make `estimation_target` required.

**Step 5: Add CausalFlow-compatible time-series block**

Add root property:

```json
"time_series": {
  "type": "object",
  "required": ["enabled"],
  "additionalProperties": false,
  "properties": {
    "enabled": {"type": "boolean"},
    "time_index_column": {"type": ["string", "null"]},
    "panel_id_column": {"type": ["string", "null"]},
    "sampling_interval": {"type": ["string", "null"]},
    "min_lag": {"type": ["integer", "null"], "minimum": 0},
    "max_lag": {"type": ["integer", "null"], "minimum": 0},
    "observation_window": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "required": ["start", "end"],
      "properties": {
        "start": {"type": "string", "format": "date-time"},
        "end": {"type": "string", "format": "date-time"}
      }
    }
  }
}
```

Make `time_series` required with `enabled: false` for static DCEs.

**Step 6: Add lag to causal edges**

Add:

```json
"lag": {"type": ["integer", "null"], "minimum": 0},
"edge_source": {
  "type": "string",
  "enum": ["expert", "experiment_design", "causal_discovery", "market_signal", "manual_review"]
}
```

Make `edge_source` required. Leave `lag` optional unless `time_series.enabled` is true; enforce that cross-field rule in the Python validator, not JSON Schema.

---

### Task 4: Implement `scripts/validate_causal_projection.py`

**Files:**
- Create: `scripts/validate_causal_projection.py`
- Test: `tests/test_validate_causal_projection.py`

**Step 1: Implement schema validation**

Use:

```python
from jsonschema import Draft202012Validator, FormatChecker
```

Expose:

```python
def validate_json_schema(instance: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(instance), key=str)]
```

**Step 2: Implement DAG semantic validation**

Required checks:
- `variable_id` uniqueness.
- every `causal_edges[].source_variable_id` exists.
- every `causal_edges[].target_variable_id` exists.
- no cycle.
- `estimation_target.outcome_variable_id` exists and has `estimator_role == "Y"`.
- every treatment ID exists and has `estimator_role == "T"`.
- every X ID exists and has `estimator_role == "X"`.
- every W ID exists and has `estimator_role == "W"`.
- if `time_series.enabled == true`, every causal edge must have non-null `lag`.
- if `time_series.enabled == false`, lag can be null or 0.

**Step 3: Avoid NetworkX implicit-node failure**

Do not call `G.add_edge(source, target)` until after endpoint validation.

Implementation:

```python
def build_networkx_graph(projection: dict):
    import networkx as nx

    variables = {v["variable_id"]: v for v in projection["variables"]}
    graph = nx.DiGraph()
    for variable_id, attrs in variables.items():
        graph.add_node(variable_id, **attrs)
    for edge in projection["causal_edges"]:
        source = edge["source_variable_id"]
        target = edge["target_variable_id"]
        graph.add_edge(source, target, **edge)
    return graph
```

Only call after endpoint validation. If NetworkX is missing, use a pure-Python DFS fallback for CI-independent acyclicity.

**Step 4: Emit normalized topological order**

Expose:

```python
def normalize_projection(projection: dict) -> dict:
    projection = copy.deepcopy(projection)
    projection["topological_order"] = topological_sort(projection)
    return projection
```

**Step 5: Add CLI**

Run:

```bash
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json
```

Expected:

```text
[causal-projection] OK
```

---

### Task 5: Harden The Other Artifact Contracts

**Files:**
- Modify: `poc_v1/contracts/experiment_run_mapping.schema.json`
- Modify: `poc_v1/contracts/normalized_experiment_results.schema.json`
- Modify: `poc_v1/contracts/market_signal.schema.json`
- Modify: `poc_v1/contracts/recommendation.schema.json`
- Test: `tests/test_causal_projection_contracts.py`

**Step 1: Close objects**

Add `additionalProperties: false` to each root object and nested object definition.

**Step 2: Normalize ontology references**

For every `ontology_ref`, restrict `ontology_node_type` to current schema node labels:

```json
[
  "Market",
  "Stage",
  "Transition",
  "StakeholderArchetype",
  "Offering",
  "Attribute",
  "AttributeLevel",
  "Trait",
  "TraitLevel",
  "Evidence",
  "Estimate",
  "Company",
  "ExperimentRun"
]
```

Rationale: free-form strings are useful during exploration but dangerous in normalized contracts.

**Step 3: Tighten normalized estimate output**

Require:
- `estimate_id`
- `estimate_type`
- `value`
- `about`
- `subconscious_experiment_id`
- `model_version`
- `ontology_snapshot_hash`
- `estimated_at`

This mirrors the `Estimate` Pydantic model and prevents a normalized row from being "almost ready" but not actually writable.

---

### Task 6: Add Immutable W&B Artifact Identity To `ExperimentRun`

**Files:**
- Modify: `poc_v1/ontology/schema.py`
- Modify: `poc_v1/ontology/node_schemas.json`
- Modify: `poc_v1/ontology/kg_seed_contract.json`
- Modify: `poc_v1/kg_seed/experiment_runs.jsonl`
- Modify: `poc_v1/ontology/super_ego_projection.json`
- Modify: `poc_v1/MIGRATION.md`
- Test: `tests/test_causal_projection_contracts.py`

**Step 1: Bump schema**

Bump `SCHEMA_VERSION` from `1.3.0` to `1.3.1`.

Rationale: adding optional fields to a Pydantic model is a schema change. It is not a new ontology node/edge, so patch bump is enough.

**Step 2: Add nested artifact identity model**

Add:

```python
class WandbArtifactRef(BaseModel):
    entity: str
    project: str
    name: str
    type: str
    version: str
    digest: str
    qualified_name: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    url: Optional[str] = None
```

Modify `ExperimentRun`:

```python
artifact_refs: list[str] = Field(default_factory=list)
wandb_artifacts: list[WandbArtifactRef] = Field(default_factory=list)
```

Keep `artifact_refs` as a legacy display/ref field for backwards compatibility.

**Step 3: Update fixture**

Add:

```json
"wandb_artifacts": [
  {
    "entity": "why-earth",
    "project": "dev-subconscious-ai",
    "name": "amce_table",
    "type": "analytics",
    "version": "v0",
    "digest": "sha256:fixture",
    "qualified_name": "why-earth/dev-subconscious-ai/amce_table:v0",
    "aliases": ["latest"]
  }
]
```

Use a clearly fake fixture digest unless verified from W&B. Do not imply it is a real digest.

**Step 4: Regenerate generated artifacts**

Run:

```bash
python scripts/generate_kg_seed_contract.py
python scripts/generate_twenty_app.py
```

---

### Task 7: Add Valid Contract Examples

**Files:**
- Create: `poc_v1/contracts/examples/causal_dag_projection.static.valid.json`
- Create: `poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json`
- Test: `tests/test_validate_causal_projection.py`

**Step 1: Static DCE/EconML example**

Must include:
- outcome variable: `Y`, Transition ref.
- treatment variable: `T`, AttributeLevel ref.
- effect modifier: `X`, StakeholderArchetype or TraitLevel ref.
- control: `W`, Market or TraitLevel ref.
- `time_series.enabled: false`.
- no causal graph edge outside declared variables.

**Step 2: Time-series market signal example**

Must include:
- `time_series.enabled: true`.
- `time_index_column`.
- `min_lag` and `max_lag`.
- every edge has `lag`.
- market signal evidence IDs only as artifacts or Evidence refs, not KG causal edges.

**Step 3: Validate examples**

Run:

```bash
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json
python scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json
```

Expected: both pass.

---

### Task 8: Add Future-Agent Integration Notes

**Files:**
- Create: `docs/causal_projection_library_grounding.md`
- Modify: `README.md`
- Modify: `poc_v1/README.md`
- Modify: `poc_v1/ontology/ontology_spec.md`

**Step 1: Document non-negotiables**

Include:
- Ontology edges are semantic/business relationships, not causal claims.
- Causal DAG edges exist only inside projection artifacts.
- Estimates land in KG only after being tied to `ontology_snapshot_hash`.
- Recommendations remain artifacts, not graph truth.

**Step 2: Document per-library projection shape**

NetworkX:
- Node IDs are `variable_id`.
- Node attrs include ontology refs and estimator roles.
- Edge attrs include rationale, evidence IDs, edge source, lag.
- Endpoint validation happens before `DiGraph.add_edge`.

CausalNex:
- Projection variables are random variables.
- `state_space` or discretization assumptions are required for BN inference.
- Structure review is required before asserting causality.

EconML:
- `Y/T/X/W` mapping is mandatory.
- Treatment encoding and observed columns are mandatory before estimator execution.

CausalFlow:
- Use only when time-series data exists.
- Require `time_series.enabled`, `time_index_column`, `min_lag`, `max_lag`, and per-edge `lag`.

RDF/RDFLib:
- Use ontology refs and projection IDs as IRIs.
- Use named graph/dataset context for `ontology_snapshot_hash`.
- Do not equate property graph records with RDF triples without an explicit mapping.

W&B:
- Store immutable `version` and `digest`.
- Store aliases as observed metadata, never as identity.

FalkorDB:
- The property graph answers lineage and context queries.
- If nested fields are unsupported by an importer, serialize nested artifact refs in the adapter, not by weakening the ontology.

---

### Task 9: Full Verification

**Files:**
- All changed files.

**Step 1: Run targeted tests**

```bash
python -m unittest tests.test_causal_projection_contracts tests.test_validate_causal_projection -v
```

Expected: all pass.

**Step 2: Run existing verification loop**

```bash
python scripts/validate_kg_seed.py
python scripts/generate_kg_seed_contract.py --check
python scripts/generate_twenty_app.py --check
python -m unittest discover -s tests -v
bash scripts/check-doc-rot.sh
python -m py_compile poc_v1/ontology/schema.py
```

Expected: all pass.

**Step 3: Explicit forbidden-edge audit**

Run:

```bash
if grep -E -R 'CAUSES|HAS_TREATMENT|HAS_OUTCOME|AFFECTS|SUPPORTED_BY|RECOMMENDS_CHANGE_TO' \
  poc_v1/ontology/schema.py \
  poc_v1/ontology/edge_schemas.json \
  poc_v1/contracts/*.json; then
  echo "forbidden causal edge label found" >&2
  exit 1
fi
```

Expected: no output.

---

## Non-Goals

- Do not add `CAUSES`, `AFFECTS`, `HAS_TREATMENT`, `HAS_OUTCOME`, or recommendation edges to the KG.
- Do not add `CausalQuestion`, `DependentVariable`, `MarketSignal`, or `Recommendation` nodes.
- Do not install heavy causal libraries as runtime dependencies in this repo.
- Do not claim W&B artifact digests are real unless fetched from W&B.
- Do not infer causal truth from simulated results alone. The pipeline can estimate effects under a design; causal validity still depends on the design, assumptions, measurement, and confounding control.

## Implementation Order

1. Tests for current failures.
2. CI/dev validation dependencies.
3. Causal DAG schema hardening.
4. Validator script.
5. Other contract hardening.
6. W&B artifact identity and schema bump.
7. Examples.
8. Future-agent documentation.
9. Full verification and code review.
