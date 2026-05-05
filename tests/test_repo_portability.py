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
        script_names = [str(path.relative_to(ROOT)).replace("\\", "/") for path in scripts]

        missing = [str(path.relative_to(ROOT)) for path in scripts if not path.exists()]
        self.assertEqual(missing, [], f"Missing harness script(s): {missing}")

        result = subprocess.run(
            ["git", "ls-files", "--stage", "--", *script_names],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        executable_modes = {
            line.rsplit("\t", 1)[1]: line.split(maxsplit=1)[0]
            for line in result.stdout.splitlines()
            if line
        }
        not_executable = [
            name
            for name in script_names
            if executable_modes.get(name) != "100755"
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
