import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "poc_v1" / "contracts"
VALIDATOR_PATH = ROOT / "scripts" / "validate_causal_projection.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_causal_projection", VALIDATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_causal_projection"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def valid_projection() -> dict:
    return {
        "projection_id": "proj_static_consider_choose_001",
        "causal_dag_projection_version": "1.0.0",
        "ontology_snapshot_hash": "sha256:demo",
        "generated_at": "2026-05-05T12:00:00Z",
        "question": "Does high provenance visibility improve Consider to Choose movement?",
        "outcome": {
            "transition": {
                "ontology_node_type": "Transition",
                "ontology_node_id": "tr_consider_choose",
            },
            "stakeholder_archetype": {
                "ontology_node_type": "StakeholderArchetype",
                "ontology_node_id": "persona_security_buyer",
            },
            "description": "Persona moves from consideration to choice.",
        },
        "variables": [
            {
                "variable_id": "treatment_provenance_visibility",
                "role": "treatment",
                "estimator_role": "T",
                "ontology_node_type": "AttributeLevel",
                "ontology_node_id": "attr_level_prov_high",
                "observed_column": "provenance_visibility_high",
                "value_type": "binary",
                "state_space": [False, True],
                "label": "High provenance visibility",
            },
            {
                "variable_id": "outcome_consider_choose",
                "role": "outcome",
                "estimator_role": "Y",
                "ontology_node_type": "Transition",
                "ontology_node_id": "tr_consider_choose",
                "observed_column": "moved_to_choose",
                "value_type": "binary",
                "state_space": [False, True],
                "label": "Moved from Consider to Choose",
            },
            {
                "variable_id": "persona_security_buyer",
                "role": "moderator",
                "estimator_role": "X",
                "ontology_node_type": "StakeholderArchetype",
                "ontology_node_id": "persona_security_buyer",
                "observed_column": "persona_security_buyer",
                "value_type": "categorical",
                "state_space": ["security_buyer"],
                "label": "Security buyer persona",
            },
            {
                "variable_id": "market_regulatory_pressure",
                "role": "adjustment",
                "estimator_role": "W",
                "ontology_node_type": "Market",
                "ontology_node_id": "mkt_enterprise_ai_regulated",
                "observed_column": "regulatory_pressure",
                "value_type": "ordinal",
                "state_space": ["low", "medium", "high"],
                "label": "Regulatory pressure",
            },
        ],
        "estimation_target": {
            "outcome_variable_id": "outcome_consider_choose",
            "treatment_variable_ids": ["treatment_provenance_visibility"],
            "effect_modifier_variable_ids": ["persona_security_buyer"],
            "control_variable_ids": ["market_regulatory_pressure"],
        },
        "causal_edges": [
            {
                "source_variable_id": "treatment_provenance_visibility",
                "target_variable_id": "outcome_consider_choose",
                "edge_source": "experiment_design",
                "lag": None,
                "rationale": "Treatment varies the proposed product attribute level.",
                "evidence_ids": ["ev_provenance_visibility"],
            },
            {
                "source_variable_id": "market_regulatory_pressure",
                "target_variable_id": "outcome_consider_choose",
                "edge_source": "expert",
                "lag": None,
                "rationale": "Regulated markets condition adoption behavior.",
                "evidence_ids": ["ev_regulatory_pressure"],
            },
        ],
        "assumptions": [
            "Treatment assignment is randomized by experiment design.",
            "Measured controls are pre-treatment.",
        ],
        "time_series": {
            "enabled": False,
            "time_index_column": None,
            "panel_id_column": None,
            "sampling_interval": None,
            "min_lag": None,
            "max_lag": None,
            "observation_window": None,
        },
        "runtime": {
            "library": "networkx",
            "version": "3.x",
        },
    }


class ValidateCausalProjectionTest(unittest.TestCase):
    def test_contract_rejects_extra_fields_and_bad_datetime(self):
        schema = load_contract("causal_dag_projection.schema.json")
        Draft202012Validator.check_schema(schema)

        sample = valid_projection()
        sample["not_in_contract"] = "reject me"
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(sample)
        )
        self.assertTrue(any("Additional properties" in error.message for error in errors))

        validator = load_validator()
        sample = valid_projection()
        sample["generated_at"] = "not-a-date"
        errors = validator.validate_json_schema(sample, schema)
        self.assertTrue(any("date-time" in error for error in errors))

    def test_rejects_unknown_edge_endpoint(self):
        validator = load_validator()
        projection = valid_projection()
        projection["causal_edges"][0]["target_variable_id"] = "missing_variable"

        errors = validator.validate_projection(projection)

        self.assertTrue(any("unknown target_variable_id" in error for error in errors))

    def test_rejects_outcome_transition_with_wrong_ontology_type(self):
        validator = load_validator()
        projection = valid_projection()
        projection["outcome"]["transition"]["ontology_node_type"] = "Market"

        errors = validator.validate_projection(projection)

        self.assertTrue(any("Transition" in error for error in errors))

    def test_rejects_outcome_transition_mismatched_with_y_variable(self):
        validator = load_validator()
        projection = valid_projection()
        projection["outcome"]["transition"]["ontology_node_id"] = "tr_other"

        errors = validator.validate_projection(projection)

        self.assertTrue(any("outcome.transition" in error for error in errors))

    def test_rejects_estimation_target_role_collision(self):
        validator = load_validator()
        projection = valid_projection()
        projection["estimation_target"]["treatment_variable_ids"].append(
            "market_regulatory_pressure"
        )

        errors = validator.validate_projection(projection)

        self.assertTrue(any("multiple estimation roles" in error for error in errors))

    def test_rejects_duplicate_estimation_target_ids_within_role(self):
        validator = load_validator()
        projection = valid_projection()
        projection["estimation_target"]["treatment_variable_ids"].append(
            "treatment_provenance_visibility"
        )

        errors = validator.validate_projection(projection)

        self.assertTrue(any("non-unique elements" in error for error in errors))

    def test_rejects_cycles(self):
        validator = load_validator()
        projection = valid_projection()
        projection["causal_edges"].append(
            {
                "source_variable_id": "outcome_consider_choose",
                "target_variable_id": "treatment_provenance_visibility",
                "edge_source": "manual_review",
                "lag": None,
                "rationale": "Invalid same-time feedback edge.",
                "evidence_ids": [],
            },
        )

        errors = validator.validate_projection(projection)

        self.assertTrue(any("cycle" in error.lower() for error in errors))

    def test_valid_projection_emits_topological_order(self):
        validator = load_validator()
        projection = valid_projection()

        normalized = validator.normalize_projection(projection)
        order = normalized["topological_order"]
        order_index = {variable_id: index for index, variable_id in enumerate(order)}

        self.assertCountEqual(
            [variable["variable_id"] for variable in projection["variables"]],
            order,
        )
        for edge in projection["causal_edges"]:
            self.assertLess(
                order_index[edge["source_variable_id"]],
                order_index[edge["target_variable_id"]],
            )

    def test_timeseries_projection_requires_lagged_edges(self):
        validator = load_validator()
        projection = valid_projection()
        projection["time_series"] = {
            "enabled": True,
            "time_index_column": "observed_at",
            "panel_id_column": "market_id",
            "sampling_interval": "P1D",
            "min_lag": 1,
            "max_lag": 7,
            "observation_window": {
                "start": "2026-05-01T00:00:00Z",
                "end": "2026-05-05T00:00:00Z",
            },
        }
        projection["causal_edges"][0]["lag"] = None

        errors = validator.validate_projection(projection)

        self.assertTrue(any("lag" in error.lower() for error in errors))

    def test_cli_validates_projection_file(self):
        validator = load_validator()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            path = Path(handle.name)
            json.dump(valid_projection(), handle)

        try:
            self.assertEqual(0, validator.main([str(path)]))
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
