import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "poc_v1" / "ontology" / "twenty_projection.json"
SCHEMA_PATH = ROOT / "poc_v1" / "ontology" / "schema.py"

REQUIRED_METADATA_FIELDS = {
    "ontology_node_id",
    "ontology_node_type",
    "ontology_schema_version",
    "projection_version",
    "source_run_id",
    "ontology_snapshot_hash",
    "synced_at",
    "source_updated_at",
}


def load_schema():
    spec = importlib.util.spec_from_file_location("schema", SCHEMA_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["schema"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text())


class TwentyProjectionManifestTest(unittest.TestCase):
    def test_manifest_covers_schema_and_declares_surfaces(self):
        schema = load_schema()
        manifest = load_manifest()
        objects = {obj["object_name"]: obj for obj in manifest["objects"]}
        node_types = {obj["ontology_node_type"] for obj in objects.values()}

        self.assertEqual(schema.SCHEMA_VERSION, manifest["schema_version"])
        self.assertEqual(set(schema.NODE_MODELS), node_types)

        primary = {
            obj["object_name"]: obj["ontology_node_type"]
            for obj in objects.values()
            if obj["surface"] == "primary"
        }
        self.assertEqual(
            {
                "company": "Company",
                "product": "Offering",
                "persona": "StakeholderArchetype",
            },
            primary,
        )

    def test_manifest_preserves_trait_and_level_as_first_class_schema(self):
        schema = load_schema()
        manifest = load_manifest()
        support_types = {
            obj["ontology_node_type"]
            for obj in manifest["objects"]
            if obj["surface"] == "support"
        }

        self.assertIn("Trait", schema.NODE_MODELS)
        self.assertIn("TraitLevel", schema.NODE_MODELS)
        self.assertIn("Trait", support_types)
        self.assertIn("TraitLevel", support_types)

    def test_every_object_has_projection_metadata_and_ledger_keys(self):
        manifest = load_manifest()
        stable_key_fields = manifest["sync_ledger"]["stable_key_fields"]

        self.assertEqual(
            [
                "tenant_id",
                "ontology_node_type",
                "ontology_node_id",
                "ontology_snapshot_hash",
            ],
            stable_key_fields,
        )

        for obj in manifest["objects"]:
            with self.subTest(object_name=obj["object_name"]):
                field_names = {field["name"] for field in obj["fields"]}
                self.assertTrue(REQUIRED_METADATA_FIELDS.issubset(field_names))
                self.assertEqual(stable_key_fields, obj["sync_ledger_key_fields"])

    def test_manifest_links_product_and_persona_support_data(self):
        manifest = load_manifest()
        objects = {obj["object_name"]: obj for obj in manifest["objects"]}

        product_relations = {
            relation["name"]: relation
            for relation in objects["product"]["relations"]
        }
        self.assertEqual("attribute", product_relations["attributes"]["target_object"])
        self.assertEqual("HAS_ATTRIBUTE", product_relations["attributes"]["edge_label"])

        attribute_relations = {
            relation["name"]: relation
            for relation in objects["attribute"]["relations"]
        }
        self.assertEqual(
            "attribute_level",
            attribute_relations["levels"]["target_object"],
        )
        self.assertEqual("HAS_LEVEL", attribute_relations["levels"]["edge_label"])

        persona_relations = {
            relation["name"]: relation
            for relation in objects["persona"]["relations"]
        }
        self.assertEqual("trait", persona_relations["traits"]["target_object"])
        self.assertEqual("HAS_TRAIT", persona_relations["traits"]["edge_label"])

        trait_relations = {
            relation["name"]: relation
            for relation in objects["trait"]["relations"]
        }
        self.assertEqual("trait_level", trait_relations["levels"]["target_object"])
        self.assertEqual("HAS_LEVEL", trait_relations["levels"]["edge_label"])


if __name__ == "__main__":
    unittest.main()
