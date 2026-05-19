"""Tests for scripts/generate_repo_index.py — the agent-readable file/symbol index.

Mirrors tests/test_repo_map.py: the generator must stay deterministic and the
committed docs/REPO_INDEX.md must match what the source currently produces.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from generate_repo_index import build_index, INDEX_PATH  # noqa: E402


class RepoIndexTest(unittest.TestCase):
    def test_build_index_is_deterministic(self):
        # Two calls must be byte-identical, or `--check` would be flaky in CI.
        self.assertEqual(build_index(), build_index())

    def test_committed_index_is_current(self):
        # Mirrors the CI `--check` gate inside the unit suite.
        self.assertEqual(
            INDEX_PATH.read_text(),
            build_index(),
            "docs/REPO_INDEX.md is stale — run: python scripts/generate_repo_index.py",
        )

    def test_index_covers_a_known_module(self):
        # A real public symbol must be discoverable through the index.
        text = build_index()
        self.assertIn("poc_v1/ontology/identity.py", text)
        self.assertIn("to_identity()", text)


if __name__ == "__main__":
    unittest.main()
