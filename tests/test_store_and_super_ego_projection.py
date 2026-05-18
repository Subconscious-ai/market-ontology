import json
import unittest
from pathlib import Path

from poc_v1.ontology.schema import SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
SUPER_EGO_PROJECTION_PATH = ROOT / "poc_v1" / "ontology" / "super_ego_projection.json"


class StoreAndSuperEgoProjectionTest(unittest.TestCase):
    def test_live_docs_use_falkordb_property_graph_language(self):
        live_docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "poc_v1" / "MIGRATION.md",
            ROOT / "poc_v1" / "v2_spec.md",
            ROOT / "poc_v1" / "ontology" / "ontology_spec.md",
            ROOT / "poc_v1" / "ontology" / "schema.py",
        ]

        for path in live_docs:
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("Neo4j", text)
                self.assertNotIn("neo4j/", text)

        # Store technology is asserted in the ontology spec. As of the 2026-05
        # docs consolidation (#86) the README is a thin pointer doc and the
        # stale duplicate poc_v1/README.md was removed; ontology_spec.md owns
        # the stack description, so the FalkorDB drift-guard checks it there.
        spec = (ROOT / "poc_v1" / "ontology" / "ontology_spec.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("FalkorDB", spec)
        self.assertIn("property graph", spec)

    def test_neo4j_files_are_legacy_adapter_specific(self):
        self.assertFalse((ROOT / "poc_v1" / "neo4j").exists())

        adapter_dir = ROOT / "poc_v1" / "adapters" / "neo4j"
        self.assertTrue(adapter_dir.is_dir())
        self.assertEqual(
            {
                "bloom_search_phrases.cypher",
                "constraints.cypher",
                "import_jsonl.cypher",
            },
            {path.name for path in adapter_dir.glob("*.cypher")},
        )

    def test_super_ego_projection_maps_ontology_to_api_and_wandb(self):
        projection = json.loads(SUPER_EGO_PROJECTION_PATH.read_text(encoding="utf-8"))

        self.assertEqual(SCHEMA_VERSION, projection["schema_version"])
        self.assertEqual("https://api.subconscious.ai", projection["api"]["base_url"])
        self.assertEqual("why-earth", projection["wandb"]["entity"])
        self.assertEqual("dev-subconscious-ai", projection["wandb"]["project"])

        mappings = {
            item["ontology_node_type"]: item
            for item in projection["ontology_to_super_ego"]
        }
        for node_type in [
            "Attribute",
            "AttributeLevel",
            "Trait",
            "TraitLevel",
            "StakeholderArchetype",
            "Estimate",
        ]:
            self.assertIn(node_type, mappings)
            self.assertIn("api_surfaces", mappings[node_type])
            self.assertIn("wandb_surfaces", mappings[node_type])

        estimate = mappings["Estimate"]
        self.assertIn("ontology_snapshot_hash", estimate["join_keys"])
        self.assertIn("subconscious_experiment_id", estimate["join_keys"])


if __name__ == "__main__":
    unittest.main()
