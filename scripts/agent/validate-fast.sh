#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

started_at="$(date +%s)"
trap 'ended_at="$(date +%s)"; echo "validate-fast elapsed: $((ended_at - started_at))s"' EXIT

PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    PYTHON_BIN="python3"
  fi
fi

bash scripts/agent/readiness.sh
bash scripts/agent/preflight.sh
"$PYTHON_BIN" scripts/validate_causal_dag.py
"$PYTHON_BIN" scripts/validate_kg_seed.py
"$PYTHON_BIN" scripts/generate_kg_seed_contract.py --check
"$PYTHON_BIN" scripts/generate_twenty_app.py --check
"$PYTHON_BIN" scripts/generate_trustgraph_ontology.py --check
"$PYTHON_BIN" scripts/generate_repo_map.py --check
"$PYTHON_BIN" scripts/check_accepted_state_spine.py
"$PYTHON_BIN" scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.static.valid.json
"$PYTHON_BIN" scripts/validate_causal_projection.py poc_v1/contracts/examples/causal_dag_projection.timeseries.valid.json
"$PYTHON_BIN" -m unittest discover -s tests -v
bash scripts/check-doc-rot.sh
"$PYTHON_BIN" -m py_compile poc_v1/ontology/schema.py
