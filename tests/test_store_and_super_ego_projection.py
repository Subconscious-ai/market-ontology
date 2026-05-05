import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPER_EGO_PROJECTION_PATH = ROOT / "poc_v1" / "ontology" / "super_ego_projection.json"


class StoreAndSuperEgoProjectionTest(unittest.TestCase):
    def test_live_docs_use_falkordb_property_graph_language(self):
        live_docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "poc_v1" / "README.md",
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

        self.assertIn("FalkorDB", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(
            "property graph",
            (ROOT / "poc_v1" / "README.md").read_text(encoding="utf-8"),
        )

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

        self.assertEqual("1.3.1", projection["schema_version"])
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
