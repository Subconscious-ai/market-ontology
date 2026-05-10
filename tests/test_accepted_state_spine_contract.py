import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-accepted-state-spine.md"
CROSS_REPO_SMOKE = ROOT / "docs" / "accepted-state-cross-repo-smoke.md"
FIXTURE = (
    ROOT
    / "poc_v1"
    / "contracts"
    / "examples"
    / "lighthouse_projection_pack.skeleton.json"
)


class TestAcceptedStateSpineContract(unittest.TestCase):
    def test_canonical_adr_names_operating_loop_and_store_boundaries(self):
        text = ADR.read_text(encoding="utf-8")

        required = [
            "Inputs -> Evidence Inbox -> Claim Adjudicator -> Twenty Accepted Records -> Projection Pack",
            "accepted state lives in Twenty",
            "collectors produce candidates",
            "wiki and dossier are projections",
            "kg_seed is superseded by ontology_snapshot",
            "Graphiti/Falkor is a retrieval projection",
            "Zep is per-exec memory",
            "Rowboat and PageIndex are not core-path dependencies",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_change_classes_are_declared(self):
        text = ADR.read_text(encoding="utf-8")

        for index, label in {
            0: "local implementation",
            1: "local contract-adjacent",
            2: "cross-repo contract",
            3: "source-of-record / accepted-state",
            4: "breaking change",
        }.items():
            self.assertIn(f"Class {index}", text)
            self.assertIn(label, text)

    def test_drift_and_accepted_write_checks_are_registered(self):
        result = subprocess.run(
            [sys.executable, "scripts/check_accepted_state_spine.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("accepted-state-spine OK", result.stdout)

    def test_lighthouse_projection_pack_skeleton_is_minimal_and_accepted_only(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(fixture["fixture_name"], "lighthouse_projection_pack_skeleton")
        self.assertEqual(fixture["input_filter"], "accepted_only")
        self.assertEqual(fixture["source_of_record"], "twenty")
        self.assertIn("ontology_snapshot", fixture["outputs"])
        self.assertIn("sizzle_dag", fixture["outputs"])
        self.assertIn("experiment_context", fixture["outputs"])
        self.assertEqual(fixture["parking_lot"], ["zep", "rowboat", "pageindex", "linkml"])

    def test_cross_repo_smoke_skeleton_names_each_repo_gate(self):
        text = CROSS_REPO_SMOKE.read_text(encoding="utf-8")

        required = [
            "market-ontology",
            "spice-harvester",
            "ai-chatbot",
            "accepted state lives in Twenty",
            "source-of-truth drift",
            "accepted-write boundary",
            "Projection Pack",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_legacy_truth_paths_are_demoted_or_parked(self):
        text = ADR.read_text(encoding="utf-8")

        required = [
            "wiki/dossier | Projection only; generated from accepted records where possible",
            "kg_seed | Compatibility name for generated ontology_snapshot",
            "wiki/claims.jsonl | Compatibility adapter only; log usage",
            "Spice accepted writes | Blocked; Spice produces candidates only",
            "Graphiti/Falkor | Retrieval projection only; never accepted state",
            "Sizzle DAG | Accepted structure view only; not canonical",
            "raw chunks | Extraction material only; not accepted Evidence",
            "Zep | Per-exec memory only; not ontology truth",
            "Rowboat | Parked optional input lane; not core path",
            "PageIndex | Parked long-document source index; not core path",
            "LinkML | Deferred migration candidate; do not redesign schema",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_cleanup_loop_and_deletion_policy_are_declared(self):
        text = ADR.read_text(encoding="utf-8")

        required = [
            "Inventory old lanes and data paths",
            "Compatibility only",
            "Delete candidate",
            "Delete obsolete code paths aggressively",
            "Archive provenance carefully",
            "Never delete lineage needed to explain a past decision or experiment",
            "One accepted state. Many inputs. Many projections. No ghost canons.",
            "status = archived",
            "valid_to",
            "superseded_by",
            "source_ref",
            "content hash",
            "retrieval lane/query",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_drift_checker_catches_legacy_truth_regressions(self):
        checker = _load_drift_checker()
        bad_text = "\n".join(
            [
                "The Sizzle DAG is accepted truth for the app.",
                "raw chunks are loaded into Twenty as Evidence.",
                "Graphiti owns accepted state.",
                "kg_seed is the source of truth for accepted ontology state.",
                "wiki is the source of truth for accepted claims.",
                "candidate claims enter experiment context by default.",
            ]
        )

        errors = checker._check_forbidden(Path("bad.md"), bad_text)

        self.assertGreaterEqual(len(errors), 6)


def _load_drift_checker():
    spec = importlib.util.spec_from_file_location(
        "check_accepted_state_spine",
        ROOT / "scripts" / "check_accepted_state_spine.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
