"""Tests for the canonical ontology IRI scheme (issue #72).

Run from the market-ontology root with stdlib unittest:

    python3 -m unittest tests.test_iri -v

Every ontology node, class, edge predicate, and literal property gets a
stable, dereferenceable IRI under one namespace, so RDF / TrustGraph
projections and PROV-O references are unambiguous across consumers. The
invariants that matter: every `to_*`/`parse_*` pair round-trips *exactly*
(an id is never mangled or mis-split), and the four IRI kinds — instance,
class, predicate, property — never collide.
"""
import unittest
from urllib.parse import urlparse


class TestToIri(unittest.TestCase):
    def test_node_iri_shape(self):
        from poc_v1.ontology.iri import BASE_NAMESPACE, to_iri

        self.assertEqual(
            to_iri("Market", "acme_io"), f"{BASE_NAMESPACE}/Market/acme_io"
        )

    def test_rejects_empty_class(self):
        from poc_v1.ontology.iri import to_iri

        with self.assertRaises(ValueError):
            to_iri("", "acme_io")

    def test_rejects_empty_id(self):
        """An empty id mints `.../Market/` — a different node's IRI is one
        keystroke away. Refuse it loudly."""
        from poc_v1.ontology.iri import to_iri

        with self.assertRaises(ValueError):
            to_iri("Market", "")

    def test_rejects_slash_in_class(self):
        """A '/' in the class segment would let `("Market/a", "b")` collide
        with `("Market", "a/b")` — the exact ambiguity the scheme forbids."""
        from poc_v1.ontology.iri import to_iri

        with self.assertRaises(ValueError):
            to_iri("Market/x", "acme")

    def test_rejects_lowercase_class(self):
        """Node classes are PascalCase; reserving lowercase keeps the
        `class/`, `predicate/`, `property/` segments structurally
        un-collidable with any instance IRI."""
        from poc_v1.ontology.iri import to_iri

        with self.assertRaises(ValueError):
            to_iri("predicate", "ABOUT")


class TestRoundTrip(unittest.TestCase):
    def test_simple_round_trip(self):
        from poc_v1.ontology.iri import parse_iri, to_iri

        self.assertEqual(
            parse_iri(to_iri("Offering", "offering-123")),
            ("Offering", "offering-123"),
        )

    def test_round_trip_id_with_slash_and_spaces(self):
        """An id containing '/' must survive percent-encoded — it must never
        leak a path segment that `parse_iri` could mis-split."""
        from poc_v1.ontology.iri import parse_iri, to_iri

        node_id = "weird/id with spaces"
        self.assertEqual(
            parse_iri(to_iri("Evidence", node_id)), ("Evidence", node_id)
        )

    def test_round_trip_unicode_id(self):
        from poc_v1.ontology.iri import parse_iri, to_iri

        node_id = "société-café-日本"
        self.assertEqual(
            parse_iri(to_iri("Company", node_id)), ("Company", node_id)
        )

    def test_round_trip_every_node_class(self):
        """The scheme must cover the whole schema, not a hand-picked subset:
        every NODE_MODELS class mints and parses back exactly."""
        from poc_v1.ontology.iri import parse_iri, to_iri
        from poc_v1.ontology.schema import NODE_MODELS

        for cls_name in NODE_MODELS:
            with self.subTest(cls=cls_name):
                self.assertEqual(
                    parse_iri(to_iri(cls_name, "sample-id")),
                    (cls_name, "sample-id"),
                )

    def test_parse_iri_rejects_foreign_base(self):
        from poc_v1.ontology.iri import parse_iri

        with self.assertRaises(ValueError):
            parse_iri("https://example.com/Market/acme")

    def test_parse_iri_rejects_predicate_iri(self):
        """`parse_iri` and `parse_predicate_iri` are not interchangeable —
        feeding one the other's IRI is a bug and must fail loud."""
        from poc_v1.ontology.iri import parse_iri, predicate_iri

        with self.assertRaises(ValueError):
            parse_iri(predicate_iri("ABOUT"))


class TestNoCollision(unittest.TestCase):
    def test_slash_in_id_does_not_collide(self):
        from poc_v1.ontology.iri import to_iri

        self.assertNotEqual(to_iri("Market", "a/b"), to_iri("Market", "a"))

    def test_trailing_slash_id_is_distinct(self):
        from poc_v1.ontology.iri import to_iri

        self.assertNotEqual(to_iri("Trait", "x"), to_iri("Trait", "x/"))

    def test_four_iri_kinds_are_disjoint(self):
        """Instance, class, predicate, and property IRIs must form four
        disjoint namespaces — nothing in the projection may be ambiguous."""
        from poc_v1.ontology.iri import (
            class_iri,
            predicate_iri,
            property_iri,
            to_iri,
        )
        from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS

        instance = {to_iri(c, e) for c in NODE_MODELS for e in EDGE_MODELS}
        classes = {class_iri(c) for c in NODE_MODELS}
        predicates = {predicate_iri(e) for e in EDGE_MODELS}
        properties = {property_iri(p) for p in ("id", "schema_version", "value")}
        kinds = [instance, classes, predicates, properties]
        for i in range(len(kinds)):
            for j in range(i + 1, len(kinds)):
                self.assertEqual(kinds[i] & kinds[j], set())


class TestClassIri(unittest.TestCase):
    def test_class_iri_shape(self):
        from poc_v1.ontology.iri import BASE_NAMESPACE, class_iri

        self.assertEqual(class_iri("Market"), f"{BASE_NAMESPACE}/class/Market")

    def test_class_iri_rejects_lowercase(self):
        from poc_v1.ontology.iri import class_iri

        with self.assertRaises(ValueError):
            class_iri("market")


class TestPredicateIri(unittest.TestCase):
    def test_predicate_iri_shape(self):
        from poc_v1.ontology.iri import BASE_NAMESPACE, predicate_iri

        self.assertEqual(
            predicate_iri("HAS_ATTRIBUTE"),
            f"{BASE_NAMESPACE}/predicate/HAS_ATTRIBUTE",
        )

    def test_predicate_round_trip_every_edge(self):
        from poc_v1.ontology.iri import parse_predicate_iri, predicate_iri
        from poc_v1.ontology.schema import EDGE_MODELS

        for edge_name in EDGE_MODELS:
            with self.subTest(edge=edge_name):
                self.assertEqual(
                    parse_predicate_iri(predicate_iri(edge_name)), edge_name
                )

    def test_parse_predicate_iri_rejects_node_iri(self):
        from poc_v1.ontology.iri import parse_predicate_iri, to_iri

        with self.assertRaises(ValueError):
            parse_predicate_iri(to_iri("Market", "acme"))


class TestPropertyIri(unittest.TestCase):
    def test_property_iri_round_trip(self):
        from poc_v1.ontology.iri import parse_property_iri, property_iri

        self.assertEqual(
            parse_property_iri(property_iri("schema_version")),
            "schema_version",
        )

    def test_property_iri_rejects_empty(self):
        from poc_v1.ontology.iri import property_iri

        with self.assertRaises(ValueError):
            property_iri("")

    def test_parse_property_iri_rejects_predicate_iri(self):
        from poc_v1.ontology.iri import parse_property_iri, predicate_iri

        with self.assertRaises(ValueError):
            parse_property_iri(predicate_iri("ABOUT"))


class TestUrlSafety(unittest.TestCase):
    def test_all_iris_are_valid_urls(self):
        """Hostile ids (whitespace, query/fragment chars) must not leak raw
        into the IRI — the projection emits these straight into RDF."""
        from poc_v1.ontology.iri import predicate_iri, to_iri
        from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS

        hostile = "id with spaces & symbols/?#"
        iris = [to_iri(c, hostile) for c in NODE_MODELS]
        iris += [predicate_iri(e) for e in EDGE_MODELS]
        for iri in iris:
            with self.subTest(iri=iri):
                parsed = urlparse(iri)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, "ontology.subconscious.ai")
                self.assertNotIn(" ", iri)
                self.assertEqual(parsed.query, "")
                self.assertEqual(parsed.fragment, "")


if __name__ == "__main__":
    unittest.main()
