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


if __name__ == "__main__":
    unittest.main()
