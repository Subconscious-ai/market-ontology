"""Tests for the TrustGraph ontology projection (issue #71).

Run from the market-ontology root with stdlib unittest:

    python3 -m unittest tests.test_trustgraph_ontology -v

`scripts/generate_trustgraph_ontology.py` derives a TrustGraph-conformant
projection of the canonical ontology entirely from NODE_MODELS / EDGE_MODELS
+ the IRI scheme, so it cannot drift. These tests assert the committed
artifact covers the whole schema, uses canonical IRIs, carries the W3C
PROV-O lineage mapping, and stays in sync (the CI `--check` gate).
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "poc_v1" / "ontology" / "trustgraph_ontology.json"
TRIPLE_ARTIFACT = ROOT / "poc_v1" / "ontology" / "trustgraph_projection.json"
TTL_ARTIFACT = ROOT / "poc_v1" / "ontology" / "trustgraph_projection.ttl"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty"
OWL_DATATYPE_PROPERTY = "http://www.w3.org/2002/07/owl#DatatypeProperty"


def _triple_set(path: Path) -> set[tuple[str, str, str]]:
    payload = json.loads(path.read_text())
    return {
        (row["subject"], row["predicate"], row["object"])
        for row in payload["triples"]
    }


class TestTrustGraphProjection(unittest.TestCase):
    def _load(self):
        return json.loads(ARTIFACT.read_text())

    def test_projection_covers_every_node_and_edge(self):
        """The projection must mirror the *whole* schema — a node or edge
        missing from it is silent drift the TG layer would never catch."""
        from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS

        proj = self._load()
        self.assertEqual(
            {c["name"] for c in proj["classes"]}, set(NODE_MODELS)
        )
        self.assertEqual(
            {p["name"] for p in proj["predicates"]}, set(EDGE_MODELS)
        )

    def test_class_and_property_iris_come_from_iri_module(self):
        from poc_v1.ontology import iri

        proj = self._load()
        for c in proj["classes"]:
            self.assertEqual(c["iri"], iri.class_iri(c["name"]))
            for p in c["properties"]:
                self.assertEqual(p["iri"], iri.property_iri(p["name"]))

    def test_predicate_iri_and_domain_range(self):
        from poc_v1.ontology import iri

        proj = self._load()
        has_attr = next(
            p for p in proj["predicates"] if p["name"] == "HAS_ATTRIBUTE"
        )
        self.assertEqual(has_attr["iri"], iri.predicate_iri("HAS_ATTRIBUTE"))
        self.assertIn("Offering", has_attr["domain"])
        self.assertIn("Attribute", has_attr["range"])

    def test_classes_and_predicates_carry_docstring_prose(self):
        """#83 — every class/predicate must project its schema docstring as
        `comment`. The TrustGraph extraction prompt renders this prose; an
        empty comment leaves the LLM extracting against bare type names."""
        import inspect

        from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS

        proj = self._load()
        for c in proj["classes"]:
            doc = inspect.getdoc(NODE_MODELS[c["name"]])
            self.assertTrue(
                doc, f"{c['name']} model has no docstring to project"
            )
            expected = " ".join(doc.split("\n\n", 1)[0].split())
            self.assertEqual(c["comment"], expected, c["name"])
        for p in proj["predicates"]:
            self.assertTrue(
                p.get("comment"),
                f"predicate {p['name']} has no projected comment",
            )
            self.assertEqual(
                p["comment"],
                " ".join(
                    inspect.getdoc(EDGE_MODELS[p["name"]])
                    .split("\n\n", 1)[0]
                    .split()
                ),
                p["name"],
            )

    def test_prov_o_lineage_mapping(self):
        """The PROV-O mapping is the point of the projection — verify the
        lineage classes/edges land on the right PROV-O terms."""
        proj = self._load()
        classes = proj["prov_o"]["classes"]
        predicates = proj["prov_o"]["predicates"]
        self.assertEqual(classes["ExperimentRun"], "prov:Activity")
        self.assertEqual(classes["Estimate"], "prov:Entity")
        self.assertEqual(classes["Evidence"], "prov:Entity")
        self.assertEqual(predicates["CONSUMED"], "prov:used")
        self.assertEqual(predicates["PRODUCED"], "prov:wasGeneratedBy")
        self.assertEqual(predicates["SUPPORTS"], "prov:wasDerivedFrom")

    def test_required_fields_are_flagged(self):
        """`required` is the lightweight cardinality signal — a required
        schema field surfaces as required:true, an Optional one as false."""
        proj = self._load()
        ev = next(c for c in proj["classes"] if c["name"] == "Evidence")
        by_name = {p["name"]: p for p in ev["properties"]}
        self.assertTrue(by_name["id"]["required"])
        self.assertFalse(by_name["agent_id"]["required"])

    def test_check_mode_is_idempotent(self):
        """The committed artifact must already match a fresh regeneration —
        the CI `--check` gate (and drift protection) depends on it."""
        result = subprocess.run(
            [sys.executable, "scripts/generate_trustgraph_ontology.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_axioms_and_projection_shape(self):
        proj = self._load()
        axioms = proj["axioms"]

        self.assertTrue(
            any(
                axiom["type"] == "owl:minCardinality"
                and axiom["subject"] == "https://ontology.subconscious.ai/class/Evidence"
                and axiom["predicate"] == "https://ontology.subconscious.ai/property/id"
                and axiom["value"] == 1
                for axiom in axioms
            )
        )
        self.assertTrue(
            any(
                axiom["type"] == "owl:oneOf"
                and axiom["subject"] == "https://ontology.subconscious.ai/class/StakeholderArchetype"
                and axiom["predicate"] == "https://ontology.subconscious.ai/property/archetype_type"
                and isinstance(axiom.get("values"), list)
                and axiom["values"]
                for axiom in axioms
            )
        )

    def test_triple_projection_is_triple_clean(self):
        triples = _triple_set(TRIPLE_ARTIFACT)

        evidence_class = "https://ontology.subconscious.ai/class/Evidence"
        transition_class = "https://ontology.subconscious.ai/class/Transition"
        offering_class = "https://ontology.subconscious.ai/class/Offering"
        has_attr_predicate = "https://ontology.subconscious.ai/predicate/HAS_ATTRIBUTE"
        schema_version_prop = "https://ontology.subconscious.ai/property/schema_version"

        self.assertIn((evidence_class, RDF_TYPE, OWL_CLASS), triples)
        self.assertIn((offering_class, RDF_TYPE, OWL_CLASS), triples)
        self.assertIn((has_attr_predicate, RDF_TYPE, OWL_OBJECT_PROPERTY), triples)
        self.assertIn((schema_version_prop, RDF_TYPE, OWL_DATATYPE_PROPERTY), triples)
        self.assertIn(
            (
                offering_class,
                has_attr_predicate,
                "https://ontology.subconscious.ai/class/Attribute",
            ),
            triples,
        )
        self.assertIn(
            (
                "https://ontology.subconscious.ai/property/name",
                "http://www.w3.org/2000/01/rdf-schema#domain",
                transition_class,
            ),
            triples,
        )
        self.assertIn(
            (
                "https://ontology.subconscious.ai/property/name",
                "http://www.w3.org/2000/01/rdf-schema#range",
                "http://www.w3.org/2001/XMLSchema#string",
            ),
            triples,
        )

    def test_ttl_projection_is_written_and_non_empty(self):
        text = TTL_ARTIFACT.read_text(encoding="utf-8")
        self.assertIn("@prefix tg:", text)
        self.assertIn("schema_version=", text)
        self.assertIn("<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>", text)

    def test_projection_artifact_has_expected_schema_fields(self):
        projection = json.loads(TRIPLE_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(projection["schema_version"], "1.6.0")
        self.assertEqual(
            projection["namespace"], "https://ontology.subconscious.ai"
        )
        self.assertIn("triples", projection)
        self.assertTrue(len(projection["triples"]) > 0)


if __name__ == "__main__":
    unittest.main()
