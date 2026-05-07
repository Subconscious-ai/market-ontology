"""Glossary display helpers."""
from __future__ import annotations


def normalize_glossary_term(term: str) -> str:
    """Trim a glossary term and collapse internal whitespace for display."""
    return " ".join(term.split())


__all__ = ["normalize_glossary_term"]
