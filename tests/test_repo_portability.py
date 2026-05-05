import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepoPortabilityTest(unittest.TestCase):
    def test_agent_harness_scripts_exist_and_are_executable(self):
        scripts = [
            ROOT / "scripts" / "agent" / "preflight.sh",
            ROOT / "scripts" / "agent" / "validate-fast.sh",
            ROOT / "scripts" / "agent" / "validate-full.sh",
            ROOT / "scripts" / "agent" / "smoke.sh",
        ]

        missing = [str(path.relative_to(ROOT)) for path in scripts if not path.exists()]
        self.assertEqual(missing, [], f"Missing harness script(s): {missing}")

        not_executable = [
            str(path.relative_to(ROOT))
            for path in scripts
            if path.exists() and not path.stat().st_mode & 0o111
        ]
        self.assertEqual(
            not_executable, [], f"Harness script(s) not executable: {not_executable}"
        )

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
