"""Tests for scripts/generate_repo_map.py — the agent-readable repo map.

Why these tests matter: the generated map replaces hand-written prose that
rotted (the old poc_v1/README.md claimed 13 nodes when the schema had 14).
These tests fail if the generator stops being deterministic or stops deriving
its counts from the live schema — i.e. if it could rot again.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from generate_repo_map import build_map, MAP_PATH  # noqa: E402
from poc_v1.ontology import schema  # noqa: E402


class RepoMapTest(unittest.TestCase):
    def test_build_map_is_deterministic(self):
        # A pure function of repo state — two calls must be byte-identical,
        # or `generate_repo_map.py --check` would be flaky in CI.
        self.assertEqual(build_map(), build_map())

    def test_map_reports_live_schema_counts(self):
        # The counts come from the schema, not hand-typed prose — this is the
        # property that makes the map unable to rot the way the README did.
        text = build_map()
        self.assertIn(f"Node models ({len(schema.NODE_MODELS)})", text)
        self.assertIn(f"Edge models ({len(schema.EDGE_MODELS)})", text)
        self.assertIn(f"SCHEMA_VERSION:** `{schema.SCHEMA_VERSION}`", text)

    def test_committed_map_is_current(self):
        # Mirrors the CI `--check` gate inside the unit suite, so a stale
        # docs/REPO_MAP.md fails locally too.
        self.assertEqual(
            MAP_PATH.read_text(),
            build_map(),
            "docs/REPO_MAP.md is stale — run: python scripts/generate_repo_map.py",
        )


if __name__ == "__main__":
    unittest.main()
