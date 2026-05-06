"""Contract + invariant tests for poc_v1.ontology.graphiti_views.

The module under test derives Graphiti-compatible Pydantic view-models
from the canonical NODE_MODELS / EDGE_MODELS in schema.py. It also
builds an EDGE_TYPE_MAP keyed by (source_label, target_label) — what
Graphiti.add_episode(edge_type_map=…) needs.

These tests live alongside the schema so that any consumer (sidecar,
twenty CRM, future agents) can rely on the contract without re-deriving
the view themselves.
"""
from __future__ import annotations

import unittest

from pydantic import BaseModel


class TestEntityTypesAreCanonicalOntology(unittest.TestCase):
    """ENTITY_TYPES is derived from NODE_MODELS, no hand-rolled copies."""

    def test_loads_from_schema(self):
        from poc_v1.ontology.graphiti_views import ENTITY_TYPES

        self.assertGreater(len(ENTITY_TYPES), 0)
        for label, model in ENTITY_TYPES.items():
            self.assertIsInstance(label, str)
            self.assertTrue(issubclass(model, BaseModel))

    def test_contains_expected_canonical_nodes(self):
        from poc_v1.ontology.graphiti_views import ENTITY_TYPES

        # Canon as of 1.2.0; if a future schema drops one, this catches it.
        expected = {
            "Market", "Stage", "Transition", "StakeholderArchetype",
            "Offering", "Attribute", "AttributeLevel", "Trait", "TraitLevel",
            "Evidence", "Estimate", "Company",
        }
        self.assertEqual(set(ENTITY_TYPES) & expected, expected)

    def test_every_node_has_contract_entry(self):
        """Schema-bump-resilient invariant: every NODE_MODELS entry must
        also appear in kg_seed_contract.json's `nodes` map. Catches drift
        where someone adds a model but forgets to regenerate the contract."""
        from poc_v1.ontology.graphiti_views import ENTITY_TYPES, _CONTRACT

        contract_nodes = set(_CONTRACT["nodes"].keys())
        ontology_nodes = set(ENTITY_TYPES.keys())
        self.assertEqual(
            ontology_nodes, contract_nodes,
            f"drift: extra in ontology={ontology_nodes - contract_nodes}, "
            f"extra in contract={contract_nodes - ontology_nodes}",
        )


class TestEdgeTypesAreCanonicalOntology(unittest.TestCase):
    """EDGE_TYPES is derived from EDGE_MODELS, no hand-rolled copies."""

    def test_loads_from_schema(self):
        from poc_v1.ontology.graphiti_views import EDGE_TYPES

        self.assertGreater(len(EDGE_TYPES), 0)
        for label, model in EDGE_TYPES.items():
            self.assertIsInstance(label, str)
            self.assertTrue(issubclass(model, BaseModel))

    def test_contains_expected_canonical_edges(self):
        from poc_v1.ontology.graphiti_views import EDGE_TYPES

        expected = {
            "FROM", "TO", "IN_MARKET", "RELEVANT_TO", "ABOUT",
            "HAS_ATTRIBUTE", "HAS_LEVEL", "HAS_TRAIT", "RELEVANT_AT",
            "SUPPORTS", "OFFERED_BY",
        }
        self.assertEqual(set(EDGE_TYPES) & expected, expected)

    def test_every_edge_has_contract_entry(self):
        """Mirror of the node-side invariant."""
        from poc_v1.ontology.graphiti_views import EDGE_TYPES, _CONTRACT

        contract_edges = set(_CONTRACT["edges"].keys())
        ontology_edges = set(EDGE_TYPES.keys())
        self.assertEqual(
            ontology_edges, contract_edges,
            f"drift: extra in ontology={ontology_edges - contract_edges}, "
            f"extra in contract={contract_edges - ontology_edges}",
        )


class TestEdgeTypeMap(unittest.TestCase):
    """EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] — what
    Graphiti.add_episode(edge_type_map=…) needs.

    The contract's `from`/`to` fields can be a single string, a list,
    or '*' (any). We expand all three into concrete (from_label,
    to_label) keys.
    """

    def test_map_is_dict_keyed_by_tuple(self):
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        self.assertIsInstance(EDGE_TYPE_MAP, dict)
        for key, value in EDGE_TYPE_MAP.items():
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertIsInstance(value, list)

    def test_simple_edge_routes_correctly(self):
        """FROM is (Transition → Stage)."""
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        self.assertIn("FROM", EDGE_TYPE_MAP[("Transition", "Stage")])

    def test_offered_by_edge_routes_correctly(self):
        """OFFERED_BY is (Offering → Company)."""
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        self.assertIn("OFFERED_BY", EDGE_TYPE_MAP[("Offering", "Company")])

    def test_polymorphic_from_expands(self):
        """ABOUT has from=[Transition, Estimate], to=*."""
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        transition_keys = [
            k for k in EDGE_TYPE_MAP
            if k[0] == "Transition" and "ABOUT" in EDGE_TYPE_MAP[k]
        ]
        estimate_keys = [
            k for k in EDGE_TYPE_MAP
            if k[0] == "Estimate" and "ABOUT" in EDGE_TYPE_MAP[k]
        ]
        self.assertGreater(
            len(transition_keys), 0,
            "ABOUT should be reachable with Transition source",
        )
        self.assertGreater(
            len(estimate_keys), 0,
            "ABOUT should be reachable with Estimate source",
        )

    def test_wildcard_target_expands_to_canonical_nodes(self):
        """SUPPORTS has from=Evidence, to=*."""
        from poc_v1.ontology.graphiti_views import (
            EDGE_TYPE_MAP,
            ENTITY_TYPES,
        )

        evidence_targets = {
            k[1] for k in EDGE_TYPE_MAP
            if k[0] == "Evidence" and "SUPPORTS" in EDGE_TYPE_MAP[k]
        }
        self.assertTrue(
            set(ENTITY_TYPES.keys()).issubset(evidence_targets),
            f"missing wildcard targets: "
            f"{set(ENTITY_TYPES.keys()) - evidence_targets}",
        )

    def test_polymorphic_target_expands(self):
        """HAS_LEVEL has from=[Attribute, Trait], to=[AttributeLevel, TraitLevel]."""
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        self.assertIn("HAS_LEVEL", EDGE_TYPE_MAP[("Attribute", "AttributeLevel")])
        self.assertIn("HAS_LEVEL", EDGE_TYPE_MAP[("Trait", "TraitLevel")])

    def test_predicates_are_unique_within_a_cell(self):
        from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP

        for key, predicates in EDGE_TYPE_MAP.items():
            self.assertEqual(
                len(predicates), len(set(predicates)),
                f"duplicate predicates at {key}: {predicates}",
            )


class TestGraphitiCompatibility(unittest.TestCase):
    """ENTITY_TYPES / EDGE_TYPES go straight into Graphiti.add_episode().
    Graphiti rejects any custom-type field that collides with its own
    EntityNode/EntityEdge field names (graphiti_core/errors.py)."""

    GRAPHITI_NODE_RESERVED = {
        "uuid", "name", "group_id", "labels", "created_at",
        "name_embedding", "summary", "attributes",
    }
    GRAPHITI_EDGE_RESERVED = {
        "uuid", "group_id", "source_node_uuid", "target_node_uuid",
        "created_at", "name", "fact", "fact_embedding", "episodes",
        "expired_at", "valid_at", "invalid_at", "reference_time",
        "attributes",
    }

    def test_entity_types_have_no_reserved_node_fields(self):
        from poc_v1.ontology.graphiti_views import ENTITY_TYPES

        for label, model in ENTITY_TYPES.items():
            for field_name in model.model_fields:
                self.assertNotIn(
                    field_name, self.GRAPHITI_NODE_RESERVED,
                    f"{label} exposes reserved field {field_name!r} — "
                    f"graphiti will raise EntityTypeValidationError",
                )

    def test_edge_types_have_no_reserved_edge_fields(self):
        from poc_v1.ontology.graphiti_views import EDGE_TYPES

        for label, model in EDGE_TYPES.items():
            for field_name in model.model_fields:
                self.assertNotIn(
                    field_name, self.GRAPHITI_EDGE_RESERVED,
                    f"{label} exposes reserved field {field_name!r} — "
                    f"graphiti will raise edge validation error",
                )


class TestNoHandwrittenSchemaInViews(unittest.TestCase):
    """View models must be derived from canonical NODE_MODELS / EDGE_MODELS,
    not hand-rolled. Any field not in the canonical model is a regression."""

    def test_every_view_field_is_in_canonical(self):
        from poc_v1.ontology.graphiti_views import ENTITY_TYPES, EDGE_TYPES
        from poc_v1.ontology import schema as canonical

        for label, view in ENTITY_TYPES.items():
            cmodel = canonical.NODE_MODELS[label]
            extra = set(view.model_fields) - set(cmodel.model_fields)
            self.assertEqual(
                extra, set(),
                f"node view {label} has fields not in canonical: {extra}",
            )
        for label, view in EDGE_TYPES.items():
            cmodel = canonical.EDGE_MODELS[label]
            extra = set(view.model_fields) - set(cmodel.model_fields)
            self.assertEqual(
                extra, set(),
                f"edge view {label} has fields not in canonical: {extra}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
