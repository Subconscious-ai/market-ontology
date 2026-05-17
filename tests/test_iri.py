"""Tests for canonical ontology IRIs."""
from __future__ import annotations

import unittest


class TestOntologyIri(unittest.TestCase):
    def test_node_iri_round_trips_for_every_node_model(self):
        from poc_v1.ontology.iri import BASE_NAMESPACE, parse_iri, to_iri
        from poc_v1.ontology.schema import NODE_MODELS

        self.assertEqual(BASE_NAMESPACE, "https://ontology.subconscious.ai")
        for class_name in NODE_MODELS:
            iri = to_iri(class_name, f"{class_name.lower()}_one")
            self.assertEqual(
                parse_iri(iri),
                (class_name, f"{class_name.lower()}_one"),
            )

    def test_node_iri_is_url_safe_reversible_and_collision_resistant(self):
        from poc_v1.ontology.iri import parse_iri, to_iri

        first = to_iri("Company", "co_cafe/with spaces")
        second = to_iri("Company", "co_cafe%2Fwith spaces")

        self.assertNotEqual(first, second)
        self.assertNotIn(" ", first)
        self.assertNotIn("/with", first)
        self.assertEqual(parse_iri(first), ("Company", "co_cafe/with spaces"))
        self.assertEqual(parse_iri(second), ("Company", "co_cafe%2Fwith spaces"))

    def test_predicate_iri_is_derived_for_every_edge_model(self):
        from poc_v1.ontology.iri import predicate_iri
        from poc_v1.ontology.schema import EDGE_MODELS

        iris = {edge: predicate_iri(edge) for edge in EDGE_MODELS}

        self.assertEqual(len(set(iris.values())), len(EDGE_MODELS))
        self.assertEqual(
            iris["OFFERED_BY"],
            "https://ontology.subconscious.ai/predicate/OFFERED_BY",
        )

    def test_unknown_class_or_edge_raises(self):
        from poc_v1.ontology.iri import predicate_iri, to_iri

        with self.assertRaises(ValueError):
            to_iri("NotAClass", "x")
        with self.assertRaises(ValueError):
            predicate_iri("NOT_AN_EDGE")


if __name__ == "__main__":
    unittest.main()
