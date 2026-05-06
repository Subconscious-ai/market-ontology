import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_FAST = ROOT / "scripts" / "agent" / "validate-fast.sh"
AGENT_OBSERVABILITY = ROOT / "docs" / "agent-observability.md"
CONTRACT_DRIFT_SMOKE_MARKER = ROOT / "docs" / "contract-drift-smoke-marker.json"
KG_SEED_CONTRACT = ROOT / "poc_v1" / "ontology" / "kg_seed_contract.json"
SYMPHONY_GATE_WORKFLOW = ROOT / ".github" / "workflows" / "symphony-gate.yml"


class AgentHarnessContractTest(unittest.TestCase):
    def test_validate_fast_includes_deterministic_validation_suite(self):
        text = VALIDATE_FAST.read_text()
        expected_lines = [
            "bash scripts/agent/readiness.sh",
            "bash scripts/agent/preflight.sh",
            '"$PYTHON_BIN" scripts/validate_causal_dag.py',
            '"$PYTHON_BIN" scripts/validate_kg_seed.py',
            '"$PYTHON_BIN" scripts/generate_kg_seed_contract.py --check',
            '"$PYTHON_BIN" scripts/generate_twenty_app.py --check',
            '"$PYTHON_BIN" scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json',
            '"$PYTHON_BIN" scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json',
            '"$PYTHON_BIN" -m unittest discover -s tests -v',
            "bash scripts/check-doc-rot.sh",
            '"$PYTHON_BIN" -m py_compile poc_v1/ontology/schema.py',
        ]

        for line in expected_lines:
            self.assertIn(line, text)

    def test_agent_observability_documents_retry_metrics_contract(self):
        text = AGENT_OBSERVABILITY.read_text()

        self.assertIn("manual_rescue_count", text)
        self.assertIn("retry_count", text)

    def test_contract_drift_smoke_marker_names_generated_contract_gate(self):
        self.assertTrue(
            CONTRACT_DRIFT_SMOKE_MARKER.exists(),
            f"{CONTRACT_DRIFT_SMOKE_MARKER} must exist",
        )
        marker = json.loads(CONTRACT_DRIFT_SMOKE_MARKER.read_text(encoding="utf-8"))

        self.assertEqual(
            {
                "marker_name": "contract-drift-smoke-test",
                "repository": "market-ontology",
                "linear_issue": "BEC-1829",
                "contract_surface": "poc_v1/ontology/kg_seed_contract.json",
                "validation_command": "PYTHON=.venv/bin/python bash scripts/agent/validate-fast.sh",
                "drift_gate": "scripts/generate_kg_seed_contract.py --check",
                "product_behavior_change": False,
            },
            marker,
        )

    def test_validate_fast_fails_on_generated_contract_drift(self):
        original_text = KG_SEED_CONTRACT.read_text()
        try:
            contract = json.loads(original_text)
            contract["__contract_drift_test__"] = True
            KG_SEED_CONTRACT.write_text(json.dumps(contract, indent=2) + "\n")

            result = subprocess.run(
                [sys.executable, "scripts/generate_kg_seed_contract.py", "--check"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(
                result.returncode,
                0,
                "generate_kg_seed_contract.py --check should fail on contract drift",
            )
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            self.assertIn("kg_seed_contract.json", combined)
        finally:
            KG_SEED_CONTRACT.write_text(original_text)

    def test_symphony_gate_runs_repo_owned_harness_entrypoints(self):
        workflow = SYMPHONY_GATE_WORKFLOW.read_text()

        self.assertIn("name: Symphony Gate", workflow)
        self.assertIn("symphony-gate:", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("timeout-minutes: 15", workflow)
        self.assertIn("bash scripts/agent/readiness.sh", workflow)
        self.assertIn("bash scripts/agent/preflight.sh", workflow)
        self.assertIn("bash scripts/agent/validate-fast.sh", workflow)

    def test_symphony_gate_pins_external_github_actions(self):
        workflow = SYMPHONY_GATE_WORKFLOW.read_text()
        action_refs = [
            line.strip().removeprefix("- ").removeprefix("uses: ")
            for line in workflow.splitlines()
            if line.strip().startswith("uses: ") or line.strip().startswith("- uses: ")
        ]

        for action_ref in action_refs:
            with self.subTest(action_ref=action_ref):
                if action_ref.startswith("./"):
                    continue
                version = action_ref.split("@", 1)[1]
                self.assertRegex(version, r"^[a-f0-9]{40}$")


if __name__ == "__main__":
    unittest.main()
