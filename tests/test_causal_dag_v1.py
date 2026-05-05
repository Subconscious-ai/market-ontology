#!/usr/bin/env python3
"""Tests for causal_dag_v1: schema instantiation, NetworkX acyclicity,
edge direction validation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from causal_dag_v1 import (  # noqa: E402
    CAUSES,
    Cause,
    Confounder,
    Effect,
    Intervention,
    Mediator,
    Moderator,
    is_dag,
    validate_graph,
)


class NodeInstantiationTests(unittest.TestCase):
    def test_minimum_cause(self):
        c = Cause(name="x")
        self.assertEqual(c.name, "x")
        self.assertEqual(c.source, "interview")
        self.assertEqual(c.confidence, 0.5)
        self.assertFalse(c.manipulable)

    def test_effect_with_metric(self):
        e = Effect(name="adoption", metric="users_per_month")
        self.assertEqual(e.metric, "users_per_month")

    def test_intervention_levels(self):
        iv = Intervention(name="discount", intervention_type="categorical",
                          levels=["0%", "10%", "20%"])
        self.assertEqual(iv.levels, ["0%", "10%", "20%"])

    def test_extra_fields_rejected(self):
        with self.assertRaises(Exception):
            Cause(name="x", bogus_field=42)  # type: ignore[arg-type]

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(Exception):
            Cause(name="x", confidence=1.5)


class EdgeInstantiationTests(unittest.TestCase):
    def test_causes_minimum(self):
        e = CAUSES(start_id="c1", end_id="e1", direction="pos")
        self.assertEqual(e.direction, "pos")
        self.assertIsNone(e.effect_size)
        self.assertEqual(e.intervention, "observe")

    def test_causes_with_effect_size(self):
        e = CAUSES(start_id="c1", end_id="e1", direction="neg",
                   effect_size=-0.5, ci_low=-0.7, ci_high=-0.3,
                   intervention="do")
        self.assertEqual(e.intervention, "do")
        self.assertEqual(e.effect_size, -0.5)

    def test_invalid_direction_rejected(self):
        with self.assertRaises(Exception):
            CAUSES(start_id="c1", end_id="e1", direction="sideways")  # type: ignore[arg-type]


class IsDagTests(unittest.TestCase):
    def test_simple_dag_passes(self):
        graph = {
            "nodes": {
                "Cause": [{"id": "c1"}, {"id": "c2"}],
                "Effect": [{"id": "e1"}],
            },
            "edges": {
                "CAUSES": [
                    {"start_id": "c1", "end_id": "e1"},
                    {"start_id": "c2", "end_id": "e1"},
                ],
            },
        }
        self.assertTrue(is_dag(graph))

    def test_three_cycle_rejected(self):
        graph = {
            "nodes": {"Cause": [{"id": "a"}, {"id": "b"}, {"id": "c"}]},
            "edges": {
                "CAUSES": [
                    {"start_id": "a", "end_id": "b"},
                    {"start_id": "b", "end_id": "c"},
                    {"start_id": "c", "end_id": "a"},  # closes the cycle
                ],
            },
        }
        self.assertFalse(is_dag(graph))

    def test_self_loop_rejected(self):
        graph = {
            "nodes": {"Cause": [{"id": "x"}]},
            "edges": {
                "CAUSES": [{"start_id": "x", "end_id": "x"}],
            },
        }
        self.assertFalse(is_dag(graph))

    def test_moderates_edges_dont_block_dag(self):
        # MODERATES is not part of the directed structure — moderator
        # pointing back at the causal chain shouldn't create a cycle.
        graph = {
            "nodes": {
                "Cause": [{"id": "c1"}],
                "Effect": [{"id": "e1"}],
                "Moderator": [{"id": "m1"}],
            },
            "edges": {
                "CAUSES": [{"start_id": "c1", "end_id": "e1"}],
                "MODERATES": [{"start_id": "m1", "end_id": "e1"}],
            },
        }
        self.assertTrue(is_dag(graph))


class ValidateGraphTests(unittest.TestCase):
    def test_valid_minimal_graph(self):
        graph = {
            "nodes": {
                "Cause": [{"id": "c1", "properties": {"name": "X"}}],
                "Effect": [{"id": "e1", "properties": {"name": "Y"}}],
            },
            "edges": {
                "CAUSES": [
                    {"start_id": "c1", "end_id": "e1",
                     "properties": {"direction": "pos"}},
                ],
            },
        }
        errors, ids = validate_graph(graph)
        self.assertEqual(errors, [])
        self.assertIn("c1", ids["nodes"])
        self.assertIn("e1", ids["nodes"])

    def test_unknown_node_label_reported(self):
        graph = {"nodes": {"Mystery": [{"id": "m1", "properties": {"name": "x"}}]}, "edges": {}}
        errors, _ = validate_graph(graph)
        self.assertTrue(any("unknown node label" in e for e in errors))

    def test_invalid_node_props_reported(self):
        graph = {
            "nodes": {"Cause": [{"id": "c1", "properties": {"name": ""}}]},  # name is min_length=1
            "edges": {},
        }
        errors, _ = validate_graph(graph)
        self.assertTrue(any("c1" in e for e in errors))

    def test_cycle_reported(self):
        graph = {
            "nodes": {
                "Cause": [{"id": "a", "properties": {"name": "A"}},
                          {"id": "b", "properties": {"name": "B"}}],
            },
            "edges": {
                "CAUSES": [
                    {"start_id": "a", "end_id": "b", "properties": {"direction": "pos"}},
                    {"start_id": "b", "end_id": "a", "properties": {"direction": "pos"}},
                ],
            },
        }
        errors, _ = validate_graph(graph)
        self.assertTrue(any("cycle" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
