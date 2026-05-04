#!/usr/bin/env bash
# scripts/check-doc-rot.sh
#
# Fail CI if Markdown docs reference paths that no longer exist. Cheap way to
# keep CLAUDE.md, READMEs, and plans honest as the three-repo stack evolves.
#
# This catches the "stale path" variety of doc rot (most common failure mode
# in this codebase: README references ~/.hermes/market-intel/, code has moved
# to ~/subconscious-ai/spice-harvester/). Does NOT catch stale prose or stale
# command invocations — use human review for those.
#
# Checks:
#   1. Forbidden substrings that mean "this doc is talking about retired code"
#   2. All ../spice-harvester and ../market-ontology paths referenced in docs
#      exist relative to the repo root (when those sibling repos are cloned)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAIL=0

# 1. Forbidden substrings — updated when retiring a path
FORBIDDEN=(
    "~/.hermes/market-intel"
    "~/.hermes/clude-harvester"
    "hermes-agent"
)

for pattern in "${FORBIDDEN[@]}"; do
    # Skip:
    # - .git (noise)
    # - this script (which must contain the pattern to search for it)
    # - any file whose first 3 lines contain `doc-rot-ok` (per-file opt-out
    #   for migration plans etc. that intentionally describe retired paths)
    hits=$(grep -rln --include="*.md" \
        --exclude-dir=.git \
        "$pattern" . 2>/dev/null \
        | grep -v "scripts/check-doc-rot.sh" \
        || true)
    # Filter out files with whole-file opt-out
    filtered=""
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        if head -3 "$f" 2>/dev/null | grep -q "doc-rot-ok"; then
            continue
        fi
        filtered="${filtered}${f}"$'\n'
    done <<< "$hits"
    hits="${filtered%$'\n'}"
    if [ -n "$hits" ]; then
        # Allow CLAUDE.md to mention the retired path ONCE inside the
        # explicit "Legacy:" paragraph. Anywhere else → failure.
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            # Count mentions. A mention is OK if the same line also contains
            # one of the "this is dead" markers below (case-insensitive) —
            # that means the author is explicitly flagging the path as gone,
            # not recommending it.
            total=$(grep -c "$pattern" "$f" || true)
            markers="legacy|retired|deprecated|deleted|moved|superseded|broken|dead|prior|REWRITE|replaces|removed|formerly|old |gone|archived"
            legacy=$(grep -cEi "($markers).*$pattern|$pattern.*($markers)" "$f" || true)
            if [ "$total" -gt "$legacy" ]; then
                echo "[doc-rot] FORBIDDEN substring '$pattern' in $f ($total mentions, $legacy flagged-as-legacy)"
                FAIL=1
            fi
        done <<< "$hits"
    fi
done

# 2. Structural paths we promise exist (check only if sibling repos are cloned)
if [ -d "../spice-harvester" ]; then
    for p in "../spice-harvester/run.sh" "../spice-harvester/lib/wiki.py"; do
        if [ ! -e "$p" ]; then
            echo "[doc-rot] missing expected sibling path: $p"
            FAIL=1
        fi
    done
fi
if [ -d "../market-ontology" ]; then
    for p in "../market-ontology/scripts/validate_kg_seed.py" "../market-ontology/poc_v1/ontology/schema.py"; do
        if [ ! -e "$p" ]; then
            echo "[doc-rot] missing expected sibling path: $p"
            FAIL=1
        fi
    done
fi

if [ "$FAIL" -eq 0 ]; then
    echo "[doc-rot] OK"
fi
exit $FAIL
