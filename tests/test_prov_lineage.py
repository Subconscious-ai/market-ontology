"""Tests for the W3C PROV-O lineage fields on the experiment-lineage nodes.

Run from the market-ontology root with stdlib unittest:

    python3 -m unittest tests.test_prov_lineage -v

TrustGraph's explainability layer expects provenance modeled with W3C
PROV-O. `Evidence` / `Estimate` / `ExperimentRun` carry an explicit
`prov:Agent` (`agent_type` + `agent_id`); `Evidence` also gains a
generation timestamp (`Estimate` already has `estimated_at`,
`ExperimentRun` has `completed_at`). Every new field is Optional, so the
1.6.0 bump is non-breaking for existing 1.5.0 records.
"""
import unittest
from datetime import datetime


class TestSchemaVersion(unittest.TestCase):
    def test_schema_version_is_1_6_0(self):
        from poc_v1.ontology.schema import SCHEMA_VERSION

        self.assertEqual(SCHEMA_VERSION, "1.6.0")


class TestProvAgentFields(unittest.TestCase):
    def test_evidence_carries_prov_agent_and_generated_at(self):
        from poc_v1.ontology.schema import Evidence

        ev = Evidence(
            id="ev-1",
            source_type="web",
            source_ref="web://x",
            agent_type="llm",
            agent_id="claude-opus-4-7",
            generated_at=datetime(2026, 5, 16, 12, 0, 0),
        )
        self.assertEqual(ev.agent_type, "llm")
        self.assertEqual(ev.agent_id, "claude-opus-4-7")
        self.assertEqual(ev.generated_at.year, 2026)

    def test_estimate_carries_prov_agent(self):
        from poc_v1.ontology.schema import Estimate

        est = Estimate(
            id="est-1",
            estimate_type="amce",
            value=0.5,
            subconscious_experiment_id="exp-1",
            model_version="v1",
            ontology_snapshot_hash="abc",
            estimated_at=datetime(2026, 5, 16),
            agent_type="subconscious_dce",
            agent_id="run-42",
        )
        self.assertEqual(est.agent_type, "subconscious_dce")
        self.assertEqual(est.agent_id, "run-42")

    def test_experiment_run_carries_prov_agent(self):
        from poc_v1.ontology.schema import ExperimentRun

        run = ExperimentRun(
            id="run-1",
            ontology_snapshot_hash="abc",
            status="finished",
            agent_type="subconscious_dce",
            agent_id="superego-9",
        )
        self.assertEqual(run.agent_type, "subconscious_dce")
        self.assertEqual(run.agent_id, "superego-9")

    def test_prov_fields_are_optional_so_1_6_0_is_non_breaking(self):
        """A 1.5.0-shaped record (no agent / generated_at) must still
        validate — the bump *adds* provenance, it does not demand it
        retroactively."""
        from poc_v1.ontology.schema import Estimate, Evidence, ExperimentRun

        ev = Evidence(id="ev-1", source_type="web", source_ref="web://x")
        self.assertIsNone(ev.agent_type)
        self.assertIsNone(ev.generated_at)

        run = ExperimentRun(
            id="r", ontology_snapshot_hash="h", status="pending"
        )
        self.assertIsNone(run.agent_id)

        est = Estimate(
            id="e",
            estimate_type="amce",
            value=0.1,
            subconscious_experiment_id="x",
            model_version="v",
            ontology_snapshot_hash="h",
            estimated_at=datetime(2026, 5, 16),
        )
        self.assertIsNone(est.agent_type)


if __name__ == "__main__":
    unittest.main()
