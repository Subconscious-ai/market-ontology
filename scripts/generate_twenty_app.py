#!/usr/bin/env python3
"""Generate/check the deterministic Twenty projection contract."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
MANIFEST_PATH = ROOT / "poc_v1" / "ontology" / "twenty_projection.json"
CONTRACT_PATH = ROOT / "poc_v1" / "ontology" / "twenty_app_contract.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def build_contract() -> dict[str, Any]:
    manifest = load_manifest()
    objects: dict[str, dict[str, Any]] = {}

    for obj in sorted(manifest["objects"], key=lambda item: item["object_name"]):
        fields = {
            field["name"]: {
                key: value
                for key, value in field.items()
                if key != "name"
            }
            for field in obj["fields"]
        }
        relations = [
            {
                "name": relation["name"],
                "edge_label": relation["edge_label"],
                "target_object": relation["target_object"],
                "cardinality": relation["cardinality"],
            }
            for relation in obj["relations"]
        ]
        objects[obj["object_name"]] = {
            "display_name": obj["display_name"],
            "ontology_node_type": obj["ontology_node_type"],
            "surface": obj["surface"],
            "fields": fields,
            "relations": relations,
            "sync_ledger_key_fields": obj["sync_ledger_key_fields"],
        }

    return {
        "schema_version": manifest["schema_version"],
        "projection_version": manifest["projection_version"],
        "manifest": MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "sync_ledger": manifest["sync_ledger"],
        "objects": objects,
    }


def contract_text() -> str:
    return json.dumps(build_contract(), indent=2, sort_keys=True) + "\n"


def write_contract(path: Path = CONTRACT_PATH) -> None:
    path.write_text(contract_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()

    text = contract_text()

    if args.check:
        if not args.output.exists():
            print(f"{args.output} is missing", file=sys.stderr)
            return 1
        current = args.output.read_text()
        if current != text:
            diff = difflib.unified_diff(
                current.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile=str(args.output),
                tofile="generated",
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"[twenty-app-contract] OK: {args.output}")
        return 0

    args.output.write_text(text)
    print(f"[twenty-app-contract] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
