import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.validate_kg_seed as validate_kg_seed  # noqa: E402


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(f"{json.dumps(record)}\n" for record in records))


class ValidateKgSeedTests(unittest.TestCase):
    def test_duplicate_node_ids_are_rejected_across_fixture_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kg_seed_dir = Path(tmpdir)
            _write_jsonl(
                kg_seed_dir / "markets.jsonl",
                [
                    {
                        "id": "duplicate-node-id",
                        "properties": {
                            "name": "Example market",
                            "definition": "A test market.",
                        },
                    }
                ],
            )
            _write_jsonl(
                kg_seed_dir / "stages.jsonl",
                [
                    {
                        "id": "duplicate-node-id",
                        "properties": {
                            "name": "awareness",
                            "definition": "A test stage.",
                        },
                    }
                ],
            )

            old_dir = validate_kg_seed.KG_SEED_DIR
            old_fixtures = validate_kg_seed.FIXTURES
            try:
                validate_kg_seed.KG_SEED_DIR = kg_seed_dir
                validate_kg_seed.FIXTURES = {
                    "markets.jsonl": ("Market", False),
                    "stages.jsonl": ("Stage", False),
                }
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = validate_kg_seed.main()
            finally:
                validate_kg_seed.KG_SEED_DIR = old_dir
                validate_kg_seed.FIXTURES = old_fixtures

        self.assertEqual(result, 1)
        self.assertIn("duplicate node id", stderr.getvalue())
        self.assertIn("duplicate-node-id", stderr.getvalue())
        self.assertIn("markets.jsonl:1", stderr.getvalue())
        self.assertIn("stages.jsonl:1", stderr.getvalue())

    def test_duplicate_node_ids_are_rejected_within_one_fixture_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kg_seed_dir = Path(tmpdir)
            _write_jsonl(
                kg_seed_dir / "markets.jsonl",
                [
                    {
                        "id": "duplicate-node-id",
                        "properties": {
                            "name": "First market",
                            "definition": "A first test market.",
                        },
                    },
                    {
                        "id": "duplicate-node-id",
                        "properties": {
                            "name": "Second market",
                            "definition": "A second test market.",
                        },
                    },
                ],
            )

            old_dir = validate_kg_seed.KG_SEED_DIR
            old_fixtures = validate_kg_seed.FIXTURES
            try:
                validate_kg_seed.KG_SEED_DIR = kg_seed_dir
                validate_kg_seed.FIXTURES = {
                    "markets.jsonl": ("Market", False),
                }
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = validate_kg_seed.main()
            finally:
                validate_kg_seed.KG_SEED_DIR = old_dir
                validate_kg_seed.FIXTURES = old_fixtures

        self.assertEqual(result, 1)
        self.assertIn("duplicate node id", stderr.getvalue())
        self.assertIn("duplicate-node-id", stderr.getvalue())
        self.assertIn("markets.jsonl:1", stderr.getvalue())
        self.assertIn("markets.jsonl:2", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
