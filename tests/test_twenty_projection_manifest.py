import json
import unittest
from pathlib import Path

from poc_v1.ontology import schema


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "poc_v1" / "ontology" / "twenty_projection.json"

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


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text())


# Nodes that the schema declares but Twenty does not yet project.
# v1.4.0 — Person is opt-in. Twenty consumers that need person-level
# identity can opt in by adding a `person` projection entry in
# twenty_projection.json later (trigger per poc_v1/v2_spec.md is "same
# individual plays role at multiple companies").
TWENTY_OPT_IN_NODES = {"Person"}


class TwentyProjectionManifestTest(unittest.TestCase):
    def test_manifest_covers_schema_and_declares_surfaces(self):
        manifest = load_manifest()
        objects = {obj["object_name"]: obj for obj in manifest["objects"]}
        node_types = {obj["ontology_node_type"] for obj in objects.values()}

        self.assertEqual(schema.SCHEMA_VERSION, manifest["schema_version"])
        required_node_types = set(schema.NODE_MODELS) - TWENTY_OPT_IN_NODES
        self.assertEqual(required_node_types, node_types)

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
