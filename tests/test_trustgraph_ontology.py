import json
import sys
import unittest
from pathlib import Path

from poc_v1.ontology import schema


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_trustgraph_ontology.py"
ONTOLOGY_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_ontology.json"
POLYMORPHIC_PROPERTIES = {"about", "hasLevel", "supports", "consumed"}


def load_generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_trustgraph_ontology",
        GENERATOR_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TrustGraphOntologyProjectionTest(unittest.TestCase):
    def test_generated_classes_match_canonical_nodes_plus_root(self):
        ontology = load_generator().build_ontology()

        self.assertEqual("1.3.1", ontology["metadata"]["schemaVersion"])
        self.assertIn("SizzlEntity", ontology["classes"])
        self.assertEqual(
            set(schema.NODE_MODELS) | {"SizzlEntity"},
            set(ontology["classes"]),
        )
        for label in schema.NODE_MODELS:
            self.assertEqual(
                "SizzlEntity",
                ontology["classes"][label]["rdfs:subClassOf"],
            )

    def test_object_properties_represent_every_canonical_edge_once(self):
        generator = load_generator()
        ontology = generator.build_ontology()
        projection = generator.load_projection()
        edge_to_property = {
            spec["edgeLabel"]: prop_id
            for prop_id, spec in projection["objectProperties"].items()
        }

        self.assertEqual(set(schema.EDGE_MODELS), set(edge_to_property))
        self.assertEqual(set(edge_to_property.values()), set(ontology["objectProperties"]))

    def test_polymorphic_properties_do_not_emit_domain_or_range(self):
        ontology = load_generator().build_ontology()

        for prop_id in POLYMORPHIC_PROPERTIES:
            prop = ontology["objectProperties"][prop_id]
            self.assertNotIn("rdfs:domain", prop)
            self.assertNotIn("rdfs:range", prop)

    def test_datatype_properties_are_the_extraction_subset(self):
        ontology = load_generator().build_ontology()

        self.assertEqual(
            {
                "sizzlId",
                "name",
                "definition",
                "schemaVersion",
                "validFrom",
                "validTo",
                "confidence",
                "sourceRef",
                "sourceUrl",
                "extractedClaim",
            },
            set(ontology["datatypeProperties"]),
        )

    def test_checked_in_artifact_matches_generator(self):
        generator = load_generator()
        expected = generator.render_ontology(generator.build_ontology())

        self.assertEqual(expected, ONTOLOGY_PATH.read_text(encoding="utf-8"))

    def test_class_projection_roster_matches_canonical_nodes(self):
        """Every Pydantic node model needs a projection.classes entry with
        label + comment. Adding/removing a model must force a projection
        update so RAG-side class metadata can't silently drift from the
        canonical schema. See sizzl-trustgraph#39."""
        generator = load_generator()
        projection = generator.load_projection()

        self.assertIn("classes", projection)
        self.assertEqual(
            set(schema.NODE_MODELS),
            set(projection["classes"]),
        )
        for label, spec in projection["classes"].items():
            self.assertIn("label", spec, f"{label} missing 'label'")
            self.assertIn("comment", spec, f"{label} missing 'comment'")
            self.assertTrue(spec["comment"], f"{label} comment is empty")
            self.assertNotEqual(
                spec["comment"],
                f"Canonical Sizzl {label} entity.",
                f"{label} still has the placeholder comment — needs real prose",
            )

    def test_generated_ontology_loads_in_trustgraph_loader(self):
        checkout = ROOT.parent / "causl.io.sizzle" / "trustgraph" / "trustgraph-flow"
        if not checkout.exists():
            self.skipTest("TrustGraph checkout not available")

        import importlib.util

        loader_path = (
            checkout / "trustgraph" / "extract" / "kg" / "ontology" / "ontology_loader.py"
        )
        spec = importlib.util.spec_from_file_location(
            "trustgraph_ontology_loader",
            loader_path,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        loader = module.OntologyLoader()
        ontology = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
        loader.update_ontologies({"sizzl-market-v1": ontology})
        loaded = loader.get_ontology("sizzl-market-v1")

        self.assertIsNotNone(loaded)
        self.assertEqual([], loaded.validate_structure())


if __name__ == "__main__":
    unittest.main()
