#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    PYTHON_BIN="python3"
  fi
fi

"$PYTHON_BIN" - <<'PY'
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
