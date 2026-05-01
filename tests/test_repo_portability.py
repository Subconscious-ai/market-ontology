import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepoPortabilityTest(unittest.TestCase):
    def test_shell_scripts_are_checked_out_with_lf_endings(self):
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", "scripts/check-doc-rot.sh"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("eol: lf", result.stdout)


if __name__ == "__main__":
    unittest.main()
