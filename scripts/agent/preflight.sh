#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import importlib.util
import sys

missing = [
    package
    for package in ("pydantic", "networkx", "jsonschema")
    if importlib.util.find_spec(package) is None
]
if missing:
    sys.exit(
        f"{', '.join(missing)} required; install repo dependencies before running agents"
    )

print(sys.version.split()[0])
PY
test -d poc_v1/kg_seed
