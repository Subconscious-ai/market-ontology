#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

required_files=(
  AGENTS.md
  docs/agent-harness.md
  docs/agent-observability.md
  .github/workflows/symphony-gate.yml
)

for file in "${required_files[@]}"; do
  test -f "$file" || {
    echo "missing required harness file: $file" >&2
    exit 1
  }
done

for script in scripts/agent/preflight.sh scripts/agent/validate-fast.sh scripts/agent/validate-full.sh scripts/agent/smoke.sh scripts/agent/readiness.sh; do
  test -x "$script" || {
    echo "agent script is not executable: $script" >&2
    exit 1
  }
  grep -q '^set -euo pipefail$' "$script" || {
    echo "agent script missing bash strict mode: $script" >&2
    exit 1
  }
done

for heading in "Symphony Readiness Contract" "Validation Ladder" "Known Secrets" "Deploy Evidence" "Failure Buckets"; do
  grep -q "$heading" docs/agent-harness.md || {
    echo "docs/agent-harness.md missing section: $heading" >&2
    exit 1
  }
done

grep -q "bash scripts/agent/readiness.sh" .github/workflows/symphony-gate.yml || {
  echo "symphony-gate does not run readiness.sh" >&2
  exit 1
}

grep -q "bash scripts/agent/preflight.sh" .github/workflows/symphony-gate.yml
grep -q "bash scripts/agent/validate-fast.sh" .github/workflows/symphony-gate.yml

echo "agent readiness: ok"
