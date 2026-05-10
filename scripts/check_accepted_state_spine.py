#!/usr/bin/env python3
"""Check accepted-state spine docs for source-of-truth drift."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-accepted-state-spine.md"
POINTER = ROOT / "docs" / "accepted-state-spine.md"

REQUIRED_PHRASES = [
    "accepted state lives in Twenty",
    "collectors produce candidates",
    "wiki and dossier are projections",
    "kg_seed is superseded by ontology_snapshot",
    "Graphiti/Falkor is a retrieval projection",
    "Zep is per-exec memory",
    "Rowboat and PageIndex are not core-path dependencies",
    "Accepted writes are allowed only through approved server-side ai-chatbot paths",
]

FORBIDDEN_PATTERNS = [
    r"wiki\s+(is|as|becomes)\s+(the\s+)?canonical",
    r"wiki\s+(is|as|becomes)\s+(the\s+)?source\s+of\s+truth",
    r"dossier\s+(is|as|becomes)\s+(the\s+)?canonical",
    r"dossier\s+(is|as|becomes)\s+(the\s+)?source\s+of\s+truth",
    r"kg_seed\s+(is|as|becomes)\s+(the\s+)?canonical",
    r"kg_seed\s+(is|as|becomes)\s+(the\s+)?source\s+of\s+truth",
    r"(Sizzle\s+)?DAG\s+(is|as|becomes)\s+accepted\s+truth",
    r"(Sizzle\s+)?DAG\s+(writes|creates|owns)\s+accepted",
    r"Graphiti\s+(writes|creates|owns)\s+accepted",
    r"Graphiti\s+(is|as|becomes)\s+accepted\s+truth",
    r"Zep\s+(writes|creates|owns)\s+accepted",
    r"Zep\s+(is|as|becomes)\s+accepted\s+truth",
    r"raw chunks\s+(are|as|become)\s+accepted Evidence",
    r"raw chunks\s+are\s+loaded\s+into\s+Twenty",
    r"candidate claims\s+(enter|write to)\s+experiment context by default",
]


def _read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required spine file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _check_required(text: str) -> list[str]:
    return [f"ADR missing phrase: {phrase}" for phrase in REQUIRED_PHRASES if phrase not in text]


def _check_forbidden(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(
                f"{_display_path(path)} matches forbidden drift pattern: {pattern}"
            )
    return errors


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def main() -> int:
    errors: list[str] = []
    adr_text = _read(ADR)
    pointer_text = _read(POINTER)

    errors.extend(_check_required(adr_text))
    for path, text in ((ADR, adr_text), (POINTER, pointer_text)):
        errors.extend(_check_forbidden(path, text))

    if errors:
        for error in errors:
            print(f"[accepted-state-spine] ERROR: {error}", file=sys.stderr)
        return 1

    print("[accepted-state-spine] accepted-state-spine OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
