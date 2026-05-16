import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_twenty_app.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_twenty_app", GENERATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_twenty_app"] = mod
    spec.loader.exec_module(mod)
    return mod


class GenerateTwentyAppTest(unittest.TestCase):
    def test_build_contract_is_deterministic(self):
        generator = load_generator()

        first = json.dumps(generator.build_contract(), sort_keys=True, indent=2)
        second = json.dumps(generator.build_contract(), sort_keys=True, indent=2)

        self.assertEqual(first, second)

    def test_generator_writes_same_contract_twice(self):
        generator = load_generator()

        with tempfile.TemporaryDirectory() as tmp:
            first_path = Path(tmp) / "first.json"
            second_path = Path(tmp) / "second.json"

            generator.write_contract(first_path)
            generator.write_contract(second_path)

            self.assertEqual(first_path.read_text(), second_path.read_text())

    def test_generated_contract_exposes_metadata_and_manifest_relations(self):
        generator = load_generator()
        contract = generator.build_contract()
        product = contract["objects"]["product"]
        persona = contract["objects"]["persona"]
        estimate = contract["objects"]["estimate"]
        experiment_run = contract["objects"]["experiment_run"]

        self.assertEqual("1.5.0", contract["schema_version"])
        self.assertEqual("1.0.0", contract["projection_version"])
        self.assertEqual(
            "poc_v1/ontology/twenty_projection.json",
            contract["manifest"],
        )
        self.assertIn("ontology_node_id", product["fields"])
        self.assertIn("ontology_snapshot_hash", product["fields"])
        self.assertEqual(
            {
                "name": "attributes",
                "edge_label": "HAS_ATTRIBUTE",
                "target_object": "attribute",
                "cardinality": "many",
            },
            product["relations"][0],
        )
        self.assertEqual("trait", persona["relations"][0]["target_object"])
        self.assertIn("estimated_at", estimate["fields"])
        self.assertIn("subconscious_experiment_id", experiment_run["fields"])
        self.assertTrue(
            any(
                relation["edge_label"] == "PRODUCED"
                and relation["target_object"] == "estimate"
                for relation in experiment_run["relations"]
            )
        )
        self.assertEqual(
            [
                "tenant_id",
                "ontology_node_type",
                "ontology_node_id",
                "ontology_snapshot_hash",
            ],
            contract["sync_ledger"]["stable_key_fields"],
        )


if __name__ == "__main__":
    unittest.main()
