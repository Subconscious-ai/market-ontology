"""Canonical IRIs for ontology entities and predicates.

RDF/TrustGraph projections need stable, reversible identifiers. The Pydantic
models keep compact node IDs; this module owns the public URL-safe IRI form
consumers should use when serializing those records as triples.
"""
from __future__ import annotations

from urllib.parse import quote, unquote, urlparse

from .schema import EDGE_MODELS, NODE_MODELS

BASE_NAMESPACE = "https://ontology.subconscious.ai"
CLASS_PATH = "class"
PREDICATE_PATH = "predicate"


def _encode_segment(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("IRI segment must be a non-empty string")
    return quote(value, safe="")


def to_iri(class_name: str, node_id: str) -> str:
    """Return the canonical entity IRI for a schema class and node ID."""
    if class_name not in NODE_MODELS:
        raise ValueError(f"unknown node class: {class_name!r}")
    return f"{BASE_NAMESPACE}/{_encode_segment(class_name)}/{_encode_segment(node_id)}"


def class_iri(class_name: str) -> str:
    """Return the canonical class IRI for an ontology node label."""
    if class_name not in NODE_MODELS:
        raise ValueError(f"unknown node class: {class_name!r}")
    return f"{BASE_NAMESPACE}/{CLASS_PATH}/{_encode_segment(class_name)}"


def parse_iri(iri: str) -> tuple[str, str]:
    """Parse an entity IRI produced by ``to_iri`` into ``(class, id)``."""
    if not isinstance(iri, str) or not iri:
        raise ValueError("IRI must be a non-empty string")

    parsed = urlparse(iri)
    base = urlparse(BASE_NAMESPACE)
    if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
        raise ValueError(f"IRI {iri!r} is outside {BASE_NAMESPACE}")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0] in {CLASS_PATH, PREDICATE_PATH}:
        raise ValueError(f"IRI {iri!r} is not an entity IRI")

    class_name = unquote(parts[0])
    node_id = unquote(parts[1])
    if class_name not in NODE_MODELS:
        raise ValueError(f"unknown node class in IRI: {class_name!r}")
    return class_name, node_id


def predicate_iri(edge_label: str) -> str:
    """Return the canonical predicate IRI for an ontology edge label."""
    if edge_label not in EDGE_MODELS:
        raise ValueError(f"unknown edge label: {edge_label!r}")
    return f"{BASE_NAMESPACE}/{PREDICATE_PATH}/{_encode_segment(edge_label)}"


__all__ = [
    "BASE_NAMESPACE",
    "CLASS_PATH",
    "PREDICATE_PATH",
    "class_iri",
    "parse_iri",
    "predicate_iri",
    "to_iri",
]
