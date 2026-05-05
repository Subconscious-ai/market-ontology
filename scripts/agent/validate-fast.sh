#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

bash scripts/agent/readiness.sh
python3 scripts/validate_kg_seed.py
python3 scripts/generate_kg_seed_contract.py --check
python3 scripts/generate_twenty_app.py --check
python3 -m unittest discover -s tests -v
bash scripts/check-doc-rot.sh
python3 -m py_compile poc_v1/ontology/schema.py
