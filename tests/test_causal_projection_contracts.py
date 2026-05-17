import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from poc_v1.ontology import schema as ontology_schema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "poc_v1" / "contracts"

CANONICAL_NODE_TYPES = {
    "Market",
    "Stage",
    "Transition",
    "StakeholderArchetype",
    "Offering",
    "Attribute",
    "AttributeLevel",
    "Trait",
    "TraitLevel",
    "Need",
    "Evidence",
    "Estimate",
    "Company",
    "ExperimentRun",
}

CANONICAL_EDGE_TYPES = {
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
    "ADDRESSES",
    "HAS_NEED",
    "OFFERED_BY",
    "COMPETES_WITH",
    "OFFERING_IN_MARKET",
    "TARGETS_STAKEHOLDER",
    "CONSUMED",
    "PRODUCED",
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
    return ontology_schema


def load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


class CausalProjectionContractsTest(unittest.TestCase):
    def test_schema_matches_canonical_set_and_excludes_causal_edges(self):
        schema = load_schema()

        self.assertEqual("1.6.0", schema.SCHEMA_VERSION)
        self.assertEqual(CANONICAL_NODE_TYPES, set(schema.NODE_MODELS))
        self.assertEqual(CANONICAL_EDGE_TYPES, set(schema.EDGE_MODELS))
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
        self.assertEqual(schema.ExperimentRunStatus.FINISHED, run.status)

        with self.assertRaises(ValueError):
            schema.validate_node(
                "ExperimentRun",
                {
                    "id": "experiment_run_bad_status",
                    "ontology_snapshot_hash": "sha256:demo",
                    "status": "done",
                },
            )

        with self.assertRaises(ValueError):
            schema.validate_node(
                "ExperimentRun",
                {
                    "id": "experiment_run_bad_dates",
                    "ontology_snapshot_hash": "sha256:demo",
                    "status": "finished",
                    "started_at": "2026-05-05T12:00:00Z",
                    "completed_at": "2026-05-05T11:00:00Z",
                },
            )

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

    def test_artifact_contracts_reject_empty_evidence_and_result_payloads(self):
        market_signal_contract = load_contract("market_signal.schema.json")
        recommendation_contract = load_contract("recommendation.schema.json")
        results_contract = load_contract("normalized_experiment_results.schema.json")

        market_signal = {
            "market_signal_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:demo",
            "signal_id": "signal_empty",
            "summary": "Empty signal should fail.",
            "observed_at": "2026-05-05T12:00:00Z",
            "affected_nodes": [],
            "evidence_ids": [],
        }
        self.assertTrue(
            list(Draft202012Validator(market_signal_contract).iter_errors(market_signal))
        )

        recommendation = {
            "recommendation_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:demo",
            "recommendation_id": "rec_empty",
            "target_role": "product_manager",
            "summary": "Unsupported recommendation should fail.",
            "recommended_change": {
                "target": {
                    "ontology_node_type": "Attribute",
                    "ontology_node_id": "attr_demo",
                }
            },
            "support": {},
        }
        self.assertTrue(
            list(Draft202012Validator(recommendation_contract).iter_errors(recommendation))
        )

        results = {
            "normalized_experiment_results_version": "1.0.0",
            "ontology_snapshot_hash": "sha256:demo",
            "experiment_run_id": "experiment_run_demo",
            "subconscious_experiment_id": "sub_exp_demo",
            "model_version": "hb-demo",
            "estimated_at": "2026-05-05T12:00:00Z",
            "outcome": {
                "ontology_node_type": "Transition",
                "ontology_node_id": "tr_demo",
            },
            "wandb_run": {
                "entity": "why-earth",
                "project": "dev-subconscious-ai",
                "run_id": "run_demo",
            },
            "estimates": [],
        }
        self.assertTrue(list(Draft202012Validator(results_contract).iter_errors(results)))

    def test_super_ego_projection_links_to_causal_artifact_contracts(self):
        projection = json.loads(
            (ROOT / "poc_v1" / "ontology" / "super_ego_projection.json").read_text(
                encoding="utf-8",
            ),
        )

        self.assertEqual("1.6.0", projection["schema_version"])
        self.assertCountEqual(
            [
                "poc_v1/contracts/causal_dag_projection.schema.json",
                "poc_v1/contracts/experiment_run_mapping.schema.json",
                "poc_v1/contracts/normalized_experiment_results.schema.json",
                "poc_v1/contracts/market_signal.schema.json",
                "poc_v1/contracts/recommendation.schema.json",
            ],
            projection["artifact_contracts"],
        )

    def test_run_local_mapping_keys_are_derived_not_stored(self):
        mapping_contract = load_contract("experiment_run_mapping.schema.json")

        self.assertIn("ontology_mappings", mapping_contract["required"])
        mapping_def = mapping_contract["$defs"]["ontology_mapping"]
        self.assertCountEqual(
            [
                "source_system",
                "source_field",
                "run_local_id",
                "ontology_node_type",
                "ontology_node_id",
                "role",
            ],
            mapping_def["required"],
        )
        self.assertNotIn("mapping_key", mapping_def["properties"])

        mapping = json.loads(
            (CONTRACTS_DIR / "examples" / "experiment_run_mapping.wandb.valid.json").read_text(
                encoding="utf-8",
            ),
        )
        mapping["ontology_mappings"] = [
            {
                "source_system": "super_ego",
                "source_field": "target_behavior",
                "run_local_id": "dv_001",
                "ontology_node_type": "Transition",
                "ontology_node_id": "tr_consider_choose",
                "role": "outcome",
            }
        ]
        self.assertEqual([], list(Draft202012Validator(mapping_contract).iter_errors(mapping)))

        row = mapping["ontology_mappings"][0]
        derived_key = f"{row['source_system']}:{row['source_field']}:{row['run_local_id']}"
        self.assertEqual("super_ego:target_behavior:dv_001", derived_key)

    def test_normalized_amce_wtp_and_importance_become_estimates_about_existing_nodes(self):
        schema = load_schema()
        results_contract = load_contract("normalized_experiment_results.schema.json")

        self.assertIn("subconscious_experiment_id", results_contract["required"])
        self.assertIn("model_version", results_contract["required"])
        estimate_def = results_contract["$defs"]["normalized_estimate"]
        self.assertCountEqual(
            [
                "estimate_id",
                "estimate_type",
                "value",
                "about",
                "source_wandb",
            ],
            estimate_def["required"],
        )
        for inherited_field in (
            "subconscious_experiment_id",
            "model_version",
            "ontology_snapshot_hash",
            "estimated_at",
        ):
            self.assertNotIn(inherited_field, estimate_def["properties"])
        self.assertCountEqual(
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
                    "about": {
                        "ontology_node_type": "AttributeLevel",
                        "ontology_node_id": "attr_level_prov_high",
                    },
                    "source_wandb": {
                        "artifact_name": "amce-demo",
                        "artifact_type": "analytics",
                        "artifact_version": "v0",
                        "artifact_digest": "sha256:fixture",
                        "file_path": "amce.json",
                        "row_key": "row-1",
                    },
                },
                {
                    "estimate_id": "estimate_wtp_demo",
                    "estimate_type": "wtp",
                    "value": 18000.0,
                    "about": {
                        "ontology_node_type": "AttributeLevel",
                        "ontology_node_id": "attr_level_prov_high",
                    },
                    "source_wandb": {
                        "artifact_name": "amce-demo",
                        "artifact_type": "analytics",
                        "artifact_version": "v0",
                        "artifact_digest": "sha256:fixture",
                        "file_path": "amce.json",
                        "row_key": "row-2",
                    },
                },
                {
                    "estimate_id": "estimate_importance_demo",
                    "estimate_type": "importance",
                    "value": 0.42,
                    "about": {
                        "ontology_node_type": "Transition",
                        "ontology_node_id": "tr_consider_choose",
                    },
                    "source_wandb": {
                        "artifact_name": "importance-demo",
                        "artifact_type": "analytics",
                        "artifact_version": "v0",
                        "artifact_digest": "sha256:fixture",
                        "file_path": "importance.json",
                        "row_key": "row-3",
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
