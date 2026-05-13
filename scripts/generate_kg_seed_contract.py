#!/usr/bin/env python3
"""Generate/check the machine-readable kg_seed contract."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_v1.ontology import schema  # noqa: E402

EDGE_SCHEMA_PATH = ROOT / "poc_v1" / "ontology" / "edge_schemas.json"
CONTRACT_PATH = ROOT / "poc_v1" / "ontology" / "kg_seed_contract.json"

GRAPH_TYPES = {
    "Market": "market",
    "Stage": "stage",
    "Transition": "transition",
    "StakeholderArchetype": "stakeholder",
    "Person": "person",                  # v1.4.0
    "Offering": "offering",
    "Attribute": "attribute",
    "AttributeLevel": "attribute_level",
    "Trait": "trait",
    "TraitLevel": "trait_level",
    "Evidence": "evidence",
    "Estimate": "estimate",
    "Company": "company",
    "ExperimentRun": "experiment_run",
}


def _load_fixtures() -> dict[str, tuple[str, bool]]:
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from validate_kg_seed import FIXTURES

    return FIXTURES


def build_contract() -> dict[str, Any]:
    fixtures = _load_fixtures()
    edge_schemas = json.loads(EDGE_SCHEMA_PATH.read_text())
    edge_props = edge_schemas["properties"]

    node_filenames: dict[str, str] = {}
    edge_filenames: dict[str, list[str]] = defaultdict(list)
    files: dict[str, dict[str, str]] = {}

    for filename, (label, is_edge) in fixtures.items():
        kind = "edge" if is_edge else "node"
        files[filename] = {"kind": kind, "label": label}
        if is_edge:
            edge_filenames[label].append(filename)
        else:
            node_filenames[label] = filename

    missing_graph_types = sorted(set(schema.NODE_MODELS) - set(GRAPH_TYPES))
    if missing_graph_types:
        raise SystemExit(f"GRAPH_TYPES missing node label(s): {missing_graph_types}")

    missing_node_files = sorted(set(schema.NODE_MODELS) - set(node_filenames))
    if missing_node_files:
        raise SystemExit(f"FIXTURES missing node file(s): {missing_node_files}")

    missing_edge_files = sorted(set(schema.EDGE_MODELS) - set(edge_filenames))
    if missing_edge_files:
        raise SystemExit(f"FIXTURES missing edge file(s): {missing_edge_files}")

    nodes = {
        label: {
            "filename": node_filenames[label],
            "graph_type": GRAPH_TYPES[label],
        }
        for label in schema.NODE_MODELS
    }

    edges = {}
    for label in schema.EDGE_MODELS:
        filenames = edge_filenames[label]
        edge_schema = edge_props[label]
        edges[label] = {
            "filename": filenames[0],
            "filenames": filenames,
            "from": edge_schema["from"],
            "to": edge_schema["to"],
        }

    return {
        "schema_version": schema.SCHEMA_VERSION,
        "nodes": nodes,
        "edges": edges,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    text = json.dumps(build_contract(), indent=2) + "\n"

    if args.check:
        if not CONTRACT_PATH.exists():
            print(f"{CONTRACT_PATH} is missing", file=sys.stderr)
            return 1
        current = CONTRACT_PATH.read_text()
        if current != text:
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile=str(CONTRACT_PATH),
                tofile="generated",
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"[kg-seed-contract] OK: {CONTRACT_PATH}")
        return 0

    CONTRACT_PATH.write_text(text)
    print(f"[kg-seed-contract] wrote {CONTRACT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
