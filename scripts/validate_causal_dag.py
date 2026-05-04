#!/usr/bin/env python3
"""CI gate for causal_dag_v1 fixtures.

Reads `causal_dag_v1/kg_seed/*.jsonl`, builds the canonical graph dict,
runs `causal_dag_v1.validate_graph` (Pydantic + NetworkX acyclicity).
Exit 1 on any failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from causal_dag_v1 import validate_graph  # noqa: E402


# Filename → (section, label) — every fixture must be mapped.
FIXTURES = {
    "causes.jsonl": ("nodes", "Cause"),
    "effects.jsonl": ("nodes", "Effect"),
    "mediators.jsonl": ("nodes", "Mediator"),
    "moderators.jsonl": ("nodes", "Moderator"),
    "confounders.jsonl": ("nodes", "Confounder"),
    "interventions.jsonl": ("nodes", "Intervention"),
    "edges_causes.jsonl": ("edges", "CAUSES"),
    "edges_mediates.jsonl": ("edges", "MEDIATES"),
    "edges_moderates.jsonl": ("edges", "MODERATES"),
    "edges_confounded_by.jsonl": ("edges", "CONFOUNDED_BY"),
}


def main() -> int:
    fixtures_dir = REPO_ROOT / "causal_dag_v1" / "kg_seed"
    if not fixtures_dir.exists():
        print(f"FAIL: fixtures dir missing: {fixtures_dir}", file=sys.stderr)
        return 1

    graph: dict = {"nodes": {}, "edges": {}}
    unmapped: list[str] = []

    for path in sorted(fixtures_dir.iterdir()):
        if not path.is_file() or path.suffix != ".jsonl":
            continue
        mapping = FIXTURES.get(path.name)
        if mapping is None:
            unmapped.append(path.name)
            continue
        section, label = mapping
        rows: list[dict] = []
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"FAIL: {path.name} line: {e}", file=sys.stderr)
                return 1
        graph[section].setdefault(label, []).extend(rows)

    if unmapped:
        print(
            f"FAIL: unmapped fixtures (add to FIXTURES dict): {unmapped}",
            file=sys.stderr,
        )
        return 1

    errors, ids = validate_graph(graph)
    if errors:
        print(f"FAIL: {len(errors)} validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"OK: causal_dag_v1 fixtures valid "
        f"({len(ids['nodes'])} nodes, {len(ids['edges'])} edges)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
