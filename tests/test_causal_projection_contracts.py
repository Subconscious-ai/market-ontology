import importlib.util
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "poc_v1" / "ontology" / "schema.py"
CONTRACTS_DIR = ROOT / "poc_v1" / "contracts"

BASE_NODE_TYPES = {
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
}

BASE_EDGE_TYPES = {
    "FROM",
    "TO",
    "IN_MARKET",
    "RELEVANT_TO",
    "ABOUT",
    "HAS_ATTRIBUTE",
    "HAS_LEVEL",
    "HAS_TRAIT",
    "RELEVANT_AT",
    "SUPPORTS",
    "OFFERED_BY",
}

FORBIDDEN_CAUSAL_EDGE_TYPES = {
    "CAUSES",
    "HAS_TREATMENT",
    "HAS_OUTCOME",
    "AFFECTS",
    "SUPPORTED_BY",
    "RECOMMENDS_CHANGE_TO",
}


def load_schema():
    spec = importlib.util.spec_from_file_location("schema", SCHEMA_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["schema"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


class CausalProjectionContractsTest(unittest.TestCase):
    def test_schema_adds_only_experiment_run_and_run_edges(self):
        schema = load_schema()

        self.assertEqual("1.3.1", schema.SCHEMA_VERSION)
        self.assertEqual(BASE_NODE_TYPES | {"ExperimentRun"}, set(schema.NODE_MODELS))
        self.assertEqual(BASE_EDGE_TYPES | {"CONSUMED", "PRODUCED"}, set(schema.EDGE_MODELS))
        self.assertTrue(FORBIDDEN_CAUSAL_EDGE_TYPES.isdisjoint(schema.EDGE_MODELS))

    def test_experiment_run_and_new_estimate_types_validate(self):
        schema = load_schema()

        run = schema.validate_node(
            "ExperimentRun",
            {
                "id": "experiment_run_demo",
                "ontology_snapshot_hash": "sha256:demo",
                "super_ego_run_id": "super-ego-run-1",
                "wandb_entity": "why-earth",
                "wandb_project": "dev-subconscious-ai",
                "wandb_run_id": "wandb-run-1",
                "wandb_run_name": "resolution-demo",
                "status": "finished",
                "artifact_refs": ["wandb://artifact/amce-demo"],
                "wandb_artifacts": [
                    {
                        "entity": "why-earth",
                        "project": "dev-subconscious-ai",
                        "name": "amce-demo",
                        "type": "analytics",
                        "version": "v0",
                        "digest": "sha256:fixture",
                        "qualified_name": "why-earth/dev-subconscious-ai/amce-demo:v0",
                        "aliases": ["latest"],
                    }
                ],
                "model_versions": {"expr_llm_model": "databricks-claude-sonnet-4"},
                "sample_size": 200,
                "completed_at": "2026-05-04T19:26:21Z",
            },
        )
        self.assertEqual("sha256:demo", run.ontology_snapshot_hash)
        self.assertEqual("sha256:fixture", run.wandb_artifacts[0].digest)

        amce = schema.validate_node(
            "Estimate",
            {
                "id": "estimate_amce_demo",
                "estimate_type": "amce",
                "value": 0.34,
                "ci_low": 0.19,
                "ci_high": 0.53,
                "subconscious_experiment_id": "super-ego-run-1",
                "model_version": "hb-amce",
                "ontology_snapshot_hash": "sha256:demo",
                "estimated_at": "2026-05-04T19:26:21Z",
            },
        )
        importance = schema.validate_node(
            "Estimate",
            {
                "id": "estimate_importance_demo",
                "estimate_type": "importance",
                "value": 0.42,
                "subconscious_experiment_id": "super-ego-run-1",
                "model_version": "hb-importance",
                "ontology_snapshot_hash": "sha256:demo",
                "estimated_at": "2026-05-04T19:26:21Z",
            },
        )

        self.assertEqual("amce", amce.estimate_type.value)
        self.assertEqual("importance", importance.estimate_type.value)

    def test_projection_contracts_reference_ontology_ids_not_graph_causal_edges(self):
        required_contracts = {
            "causal_dag_projection.schema.json",
            "experiment_run_mapping.schema.json",
            "normalized_experiment_results.schema.json",
            "market_signal.schema.json",
            "recommendation.schema.json",
        }

        for contract_name in required_contracts:
            with self.subTest(contract=contract_name):
                contract = load_contract(contract_name)
                Draft202012Validator.check_schema(contract)
                contract_text = json.dumps(contract)
                self.assertEqual("https://json-schema.org/draft/2020-12/schema", contract["$schema"])
                self.assertIn("ontology_snapshot_hash", contract_text)
                self.assertNotIn('"CAUSES"', contract_text)
                self.assertFalse(contract.get("additionalProperties", True))

        dag_contract = load_contract("causal_dag_projection.schema.json")
        dag_props = dag_contract["properties"]
        self.assertIn("variables", dag_props)
        self.assertIn("assumptions", dag_props)
        self.assertIn("causal_edges", dag_props)
        variable_props = dag_contract["$defs"]["ontology_variable"]["properties"]
        self.assertIn("ontology_node_type", variable_props)
        self.assertIn("ontology_node_id", variable_props)
        self.assertIn("estimator_role", variable_props)
        self.assertIn("value_type", variable_props)
        self.assertIn("observed_column", variable_props)
        self.assertIn("estimation_target", dag_props)
        self.assertIn("time_series", dag_props)

    def test_super_ego_projection_links_to_causal_artifact_contracts(self):
        projection = json.loads(
            (ROOT / "poc_v1" / "ontology" / "super_ego_projection.json").read_text(
                encoding="utf-8",
            ),
        )

        self.assertEqual("1.3.1", projection["schema_version"])
        self.assertEqual(
            [
                "poc_v1/contracts/causal_dag_projection.schema.json",
                "poc_v1/contracts/experiment_run_mapping.schema.json",
                "poc_v1/contracts/normalized_experiment_results.schema.json",
                "poc_v1/contracts/market_signal.schema.json",
                "poc_v1/contracts/recommendation.schema.json",
            ],
            projection["artifact_contracts"],
        )

    def test_run_local_ids_map_deterministically_to_ontology_ids(self):
        mapping_contract = load_contract("experiment_run_mapping.schema.json")

        self.assertIn("ontology_mappings", mapping_contract["required"])
        mapping_def = mapping_contract["$defs"]["ontology_mapping"]
        self.assertEqual(
            [
                "mapping_key",
                "source_system",
                "source_field",
                "run_local_id",
                "ontology_node_type",
                "ontology_node_id",
                "role",
            ],
            mapping_def["required"],
        )

        sample_mappings = [
            {
                "source_system": "super_ego",
                "source_field": "target_behavior",
                "run_local_id": "dv_001",
                "ontology_node_type": "Transition",
                "ontology_node_id": "tr_consider_choose",
                "role": "outcome",
            },
            {
                "source_system": "wandb",
                "source_field": "analytics_artifact.amce.Features",
                "run_local_id": "provenance_visibility=high",
                "ontology_node_type": "AttributeLevel",
                "ontology_node_id": "attr_level_prov_high",
                "role": "treatment",
            },
        ]

        keys = [
            f"{row['source_system']}:{row['source_field']}:{row['run_local_id']}"
            for row in sample_mappings
        ]
        keys_again = [
            f"{row['source_system']}:{row['source_field']}:{row['run_local_id']}"
            for row in sample_mappings
        ]
        self.assertEqual(keys, keys_again)
        self.assertEqual(len(keys), len(set(keys)))

    def test_normalized_amce_wtp_and_importance_become_estimates_about_existing_nodes(self):
        schema = load_schema()
        results_contract = load_contract("normalized_experiment_results.schema.json")

        self.assertIn("subconscious_experiment_id", results_contract["required"])
        self.assertIn("model_version", results_contract["required"])
        estimate_def = results_contract["$defs"]["normalized_estimate"]
        self.assertEqual(
            [
                "estimate_id",
                "estimate_type",
                "value",
                "about",
                "subconscious_experiment_id",
                "model_version",
                "ontology_snapshot_hash",
                "estimated_at",
                "source_wandb",
            ],
            estimate_def["required"],
        )
        self.assertEqual(
            [
                "part_worth",
                "transition_probability",
                "wtp",
                "elasticity",
                "ate",
                "amce",
                "importance",
            ],
            estimate_def["properties"]["estimate_type"]["enum"],
        )

        normalized = {
            "ontology_snapshot_hash": "sha256:demo",
            "subconscious_experiment_id": "super-ego-run-1",
            "model_version": "hb-amce-importance",
            "estimated_at": "2026-05-04T19:26:21Z",
            "estimates": [
                {
                    "estimate_id": "estimate_amce_demo",
                    "estimate_type": "amce",
                    "value": 0.34,
                    "subconscious_experiment_id": "super-ego-run-1",
                    "model_version": "hb-amce-importance",
                    "ontology_snapshot_hash": "sha256:demo",
                    "estimated_at": "2026-05-04T19:26:21Z",
                    "about": {
                        "ontology_node_type": "AttributeLevel",
                        "ontology_node_id": "attr_level_prov_high",
                    },
                },
                {
                    "estimate_id": "estimate_wtp_demo",
                    "estimate_type": "wtp",
                    "value": 18000.0,
                    "subconscious_experiment_id": "super-ego-run-1",
                    "model_version": "hb-amce-importance",
                    "ontology_snapshot_hash": "sha256:demo",
                    "estimated_at": "2026-05-04T19:26:21Z",
                    "about": {
                        "ontology_node_type": "AttributeLevel",
                        "ontology_node_id": "attr_level_prov_high",
                    },
                },
                {
                    "estimate_id": "estimate_importance_demo",
                    "estimate_type": "importance",
                    "value": 0.42,
                    "subconscious_experiment_id": "super-ego-run-1",
                    "model_version": "hb-amce-importance",
                    "ontology_snapshot_hash": "sha256:demo",
                    "estimated_at": "2026-05-04T19:26:21Z",
                    "about": {
                        "ontology_node_type": "Transition",
                        "ontology_node_id": "tr_consider_choose",
                    },
                },
            ],
        }

        for estimate in normalized["estimates"]:
            with self.subTest(estimate_type=estimate["estimate_type"]):
                validated = schema.validate_node(
                    "Estimate",
                    {
                        "id": estimate["estimate_id"],
                        "estimate_type": estimate["estimate_type"],
                        "value": estimate["value"],
                        "subconscious_experiment_id": normalized["subconscious_experiment_id"],
                        "model_version": normalized["model_version"],
                        "ontology_snapshot_hash": normalized["ontology_snapshot_hash"],
                        "estimated_at": normalized["estimated_at"],
                    },
                )
                edge = schema.validate_edge(
                    "ABOUT",
                    {
                        "start_id": estimate["estimate_id"],
                        "end_id": estimate["about"]["ontology_node_id"],
                        "target_node_type": estimate["about"]["ontology_node_type"],
                    },
                )
                self.assertEqual(estimate["estimate_type"], validated.estimate_type.value)
                self.assertEqual(estimate["about"]["ontology_node_type"], edge.target_node_type)


if __name__ == "__main__":
    unittest.main()
