import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_FAST = ROOT / "scripts" / "agent" / "validate-fast.sh"
KG_SEED_CONTRACT = ROOT / "poc_v1" / "ontology" / "kg_seed_contract.json"


class AgentHarnessContractTest(unittest.TestCase):
    def test_validate_fast_includes_deterministic_validation_suite(self):
        text = VALIDATE_FAST.read_text()
        expected_lines = [
            "python3 scripts/validate_kg_seed.py",
            "python3 scripts/generate_kg_seed_contract.py --check",
            "python3 scripts/generate_twenty_app.py --check",
            "python3 -m unittest discover -s tests -v",
            "bash scripts/check-doc-rot.sh",
            "python3 -m py_compile poc_v1/ontology/schema.py",
        ]

        for line in expected_lines:
            self.assertIn(line, text)

    def test_validate_fast_fails_on_generated_contract_drift(self):
        original_text = KG_SEED_CONTRACT.read_text()
        try:
            contract = json.loads(original_text)
            contract["__contract_drift_test__"] = True
            KG_SEED_CONTRACT.write_text(json.dumps(contract, indent=2) + "\n")

            result = subprocess.run(
                ["python3", "scripts/generate_kg_seed_contract.py", "--check"],
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


if __name__ == "__main__":
    unittest.main()
