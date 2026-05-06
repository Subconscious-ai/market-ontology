import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepairLoopProofTest(unittest.TestCase):
    def test_agent_harness_docs_record_repair_loop_marker(self):
        guide = ROOT / "docs" / "agent-harness.md"
        body = guide.read_text(encoding="utf-8")

        self.assertIn(
            "Repair loop proof marker: BEC-1825",
            body,
            "Repair the seeded CI failure by documenting the BEC-1825 repair loop marker.",
        )


if __name__ == "__main__":
    unittest.main()
