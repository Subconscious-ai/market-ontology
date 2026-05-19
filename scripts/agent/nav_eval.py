#!/usr/bin/env python3
"""Navigation eval — quantifies the agent-navigability assets (epic #90, system #4).

A deterministic A/B over a fixed set of common navigation questions. For each
question it measures:

- **coverage** — is the answer available directly from a generated asset
  (``docs/REPO_MAP.md`` / ``docs/REPO_INDEX.md``), with no source reading?
- **context cost** — bytes an agent must read to answer **with** the generated
  assets vs **without** them (the source files that otherwise hold the answer).

Each task also asserts its answering asset currently contains the correct
answer, so this eval doubles as a rot gate: ``--check`` exits non-zero if any
asset has drifted.

The byte counts are a deterministic, conservative lower bound on the real gain:
they do not count the search/grep an agent needs *without* the assets just to
discover which files to open. With the assets that search cost is zero.

Usage::

    python scripts/agent/nav_eval.py            # run, print the report
    python scripts/agent/nav_eval.py --check     # same, exit 1 if coverage < 100%
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP = "docs/REPO_MAP.md"
INDEX = "docs/REPO_INDEX.md"

# A fixed set of real navigation questions. For each: the generated asset that
# answers it, the substrings that asset must contain (answer + rot check), and
# the source files an agent must otherwise read ("without assets").
TASKS: list[dict] = [
    dict(id="node-count",
         q="How many node models exist, and what are they?",
         asset=MAP, markers=["Node models (14):", "`Transition`"],
         gold=["poc_v1/ontology/schema.py"]),
    dict(id="edge-count",
         q="How many edge models exist?",
         asset=MAP, markers=["Edge models (18):"],
         gold=["poc_v1/ontology/schema.py"]),
    dict(id="schema-version",
         q="What is the current SCHEMA_VERSION?",
         asset=MAP, markers=["SCHEMA_VERSION:** `1.6.0`"],
         gold=["poc_v1/ontology/schema.py"]),
    dict(id="public-modules",
         q="Which modules do downstream consumers import?",
         asset=MAP, markers=["Public import surface", "poc_v1.ontology.graphiti_views"],
         gold=["CLAUDE.md"]),
    dict(id="top-level-layout",
         q="What is the top-level layout and each directory's role?",
         asset=MAP, markers=["Top-level layout", "causal_dag_v1/"],
         gold=["CLAUDE.md"]),
    dict(id="identity-api",
         q="What public functions/classes does poc_v1/ontology/identity.py expose?",
         asset=INDEX,
         markers=["poc_v1/ontology/identity.py", "to_identity()", "class CompanyIdentity"],
         gold=["poc_v1/ontology/identity.py"]),
    dict(id="schema-symbols",
         q="What public classes does poc_v1/ontology/schema.py define?",
         asset=INDEX, markers=["poc_v1/ontology/schema.py", "class Offering"],
         gold=["poc_v1/ontology/schema.py"]),
    dict(id="generator-symbols",
         q="What does scripts/generate_repo_map.py expose?",
         asset=INDEX, markers=["scripts/generate_repo_map.py", "build_map()"],
         gold=["scripts/generate_repo_map.py"]),
]


def _size(rel: str) -> int:
    path = ROOT / rel
    return path.stat().st_size if path.exists() else 0


def run() -> tuple[list[dict], dict]:
    """Evaluate every task; return (per-task rows, aggregate metrics)."""
    rows: list[dict] = []
    for task in TASKS:
        asset_path = ROOT / task["asset"]
        asset_text = asset_path.read_text(encoding="utf-8") if asset_path.exists() else ""
        answered = bool(asset_text) and all(m in asset_text for m in task["markers"])
        rows.append({
            "id": task["id"],
            "q": task["q"],
            "asset": task["asset"],
            "answered": answered,
            "with_bytes": _size(task["asset"]),
            "without_bytes": sum(_size(g) for g in task["gold"]),
        })

    covered = sum(r["answered"] for r in rows)
    assets_used = sorted({t["asset"] for t in TASKS})
    gold_used = sorted({g for t in TASKS for g in t["gold"]})
    agg_with = sum(_size(a) for a in assets_used)
    agg_without = sum(_size(g) for g in gold_used)

    metrics = {
        "tasks": len(rows),
        "covered": covered,
        "coverage_pct": round(100 * covered / len(rows), 1),
        "reads_with": len(assets_used),
        "reads_without": len(gold_used),
        "bytes_with": agg_with,
        "bytes_without": agg_without,
        "byte_ratio": round(agg_without / agg_with, 2) if agg_with else 0.0,
        "assets_used": assets_used,
        "gold_used": gold_used,
    }
    return rows, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Navigation eval (epic #90 system #4)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if coverage < 100%% (an asset has drifted)",
    )
    args = parser.parse_args()

    rows, m = run()

    print("=" * 66)
    print("NAVIGATION EVAL — market-ontology agent-navigability assets (#90)")
    print("=" * 66)
    print(f"{'task':<20} {'answered from asset':<22} {'with':>7} {'without':>9}")
    print("-" * 66)
    for r in rows:
        mark = "yes — " + r["asset"].split("/")[-1] if r["answered"] else "NO"
        print(f"{r['id']:<20} {mark:<22} {r['with_bytes']:>7} {r['without_bytes']:>9}")
    print("-" * 66)
    print(f"Coverage:          {m['covered']}/{m['tasks']} tasks "
          f"answerable directly from a generated asset ({m['coverage_pct']}%)")
    print(f"Reads to answer all {m['tasks']}:  WITH assets = {m['reads_with']} files "
          f"· WITHOUT = {m['reads_without']} files")
    print(f"Bytes to answer all {m['tasks']}:  WITH = {m['bytes_with']} "
          f"· WITHOUT = {m['bytes_without']} · reduction = {m['byte_ratio']}x")
    print("=" * 66)

    if args.check and m["covered"] != m["tasks"]:
        print("[nav-eval] FAIL — an asset is stale or missing an expected answer.",
              file=sys.stderr)
        return 1
    print("[nav-eval] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
