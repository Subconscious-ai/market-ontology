"""Canonical IRI scheme for the Subconscious ontology.

Every ontology node, class, edge predicate, and literal property gets a
stable, dereferenceable IRI under one namespace, so RDF / TrustGraph
projections and PROV-O references are unambiguous and consistent across
consumers (the TrustGraph projection layer, spice-harvester ``typed_graph``
emission, future agents).

    instance   https://ontology.subconscious.ai/<Class>/<percent-encoded-id>
    class      https://ontology.subconscious.ai/class/<Class>
    predicate  https://ontology.subconscious.ai/predicate/<EDGE_NAME>
    property   https://ontology.subconscious.ai/property/<field_name>

The four kinds form four disjoint namespaces. Node classes are PascalCase
(every ``NODE_MODELS`` key); the kind markers ``class`` / ``predicate`` /
``property`` are lowercase, so a marker can never be mistaken for a class —
an instance IRI's second segment is always PascalCase, a class/predicate/
property IRI's is always one of the three lowercase markers.

IRIs are *instance-stable*: they deliberately do NOT encode the schema
version. A ``Market`` node keeps its IRI across schema bumps — linked-data
and PROV-O references must not churn when the type layer evolves.

Instance ids are percent-encoded with no safe characters, so an id
containing ``/`` can never leak a path segment that :func:`parse_iri` would
mis-split, and every ``to_*``/``parse_*`` pair round-trips exactly.

This module is intentionally schema-decoupled — it is a pure boundary
serializer (like ``identity.normalize_slug``) and does not import the
Pydantic models. It validates IRI *shape* (PascalCase class, SCREAMING_SNAKE
edge); membership in ``NODE_MODELS`` / ``EDGE_MODELS`` is the caller's
concern (the projection generator iterates the real models).

Public API::

    BASE_NAMESPACE
    to_iri(class_name, node_id)  -> str       parse_iri(iri)            -> (class, id)
    class_iri(class_name)        -> str
    predicate_iri(edge_name)     -> str       parse_predicate_iri(iri)  -> edge_name
    property_iri(field_name)     -> str       parse_property_iri(iri)   -> field_name
"""
from __future__ import annotations

import re
from urllib.parse import quote, unquote

#: The single namespace every ontology IRI lives under. Centralized here so
#: a move is a one-line change.
BASE_NAMESPACE = "https://ontology.subconscious.ai"

_CLASS_MARKER = "class"
_PREDICATE_MARKER = "predicate"
_PROPERTY_MARKER = "property"

#: Node class labels are PascalCase (every ``NODE_MODELS`` key matches).
_CLASS_RE = re.compile(r"[A-Z][A-Za-z0-9]*\Z")
#: Edge predicates are SCREAMING_SNAKE (every ``EDGE_MODELS`` key matches).
_EDGE_RE = re.compile(r"[A-Z][A-Z0-9_]*\Z")


def to_iri(class_name: str, node_id: str) -> str:
    """Mint the stable IRI for an ontology node instance.

    ``class_name`` must be a PascalCase node label (a ``NODE_MODELS`` key);
    ``node_id`` is any non-empty string and is percent-encoded in full.
    """
    _require_class(class_name)
    if not node_id:
        raise ValueError("node_id must be a non-empty string")
    return f"{BASE_NAMESPACE}/{class_name}/{quote(node_id, safe='')}"


def parse_iri(iri: str) -> tuple[str, str]:
    """Inverse of :func:`to_iri` -> ``(class_name, node_id)``.

    Raises ``ValueError`` for anything that is not a node instance IRI —
    including a class, predicate, or property IRI.
    """
    class_name, sep, encoded_id = _strip_base(iri).partition("/")
    if not sep or not encoded_id or "/" in encoded_id:
        raise ValueError(f"not a node IRI: {iri!r}")
    if not _CLASS_RE.match(class_name):
        raise ValueError(f"not a node IRI: {iri!r}")
    return class_name, unquote(encoded_id)


def class_iri(class_name: str) -> str:
    """Mint the stable IRI for an ontology node *class* (the type itself)."""
    _require_class(class_name)
    return f"{BASE_NAMESPACE}/{_CLASS_MARKER}/{class_name}"


def predicate_iri(edge_name: str) -> str:
    """Mint the stable IRI for an ontology edge predicate."""
    _require_edge(edge_name)
    return f"{BASE_NAMESPACE}/{_PREDICATE_MARKER}/{edge_name}"


def parse_predicate_iri(iri: str) -> str:
    """Inverse of :func:`predicate_iri` -> ``edge_name``."""
    marker, sep, edge_name = _strip_base(iri).partition("/")
    if marker != _PREDICATE_MARKER or not sep or not _EDGE_RE.match(edge_name):
        raise ValueError(f"not a predicate IRI: {iri!r}")
    return edge_name


def property_iri(field_name: str) -> str:
    """Mint the stable IRI for a node/edge literal property (an OWL
    datatype property), e.g. ``schema_version`` or ``value``."""
    if not field_name:
        raise ValueError("field_name must be a non-empty string")
    return f"{BASE_NAMESPACE}/{_PROPERTY_MARKER}/{quote(field_name, safe='')}"


def parse_property_iri(iri: str) -> str:
    """Inverse of :func:`property_iri` -> ``field_name``."""
    marker, sep, encoded = _strip_base(iri).partition("/")
    if marker != _PROPERTY_MARKER or not sep or not encoded or "/" in encoded:
        raise ValueError(f"not a property IRI: {iri!r}")
    return unquote(encoded)


def _require_class(class_name: str) -> None:
    if not _CLASS_RE.match(class_name or ""):
        raise ValueError(
            f"class_name must be PascalCase (a NODE_MODELS key), got {class_name!r}"
        )


def _require_edge(edge_name: str) -> None:
    if not _EDGE_RE.match(edge_name or ""):
        raise ValueError(
            f"edge_name must be a SCREAMING_SNAKE EDGE_MODELS key, got {edge_name!r}"
        )


def _strip_base(iri: str) -> str:
    """Return the path under :data:`BASE_NAMESPACE`, or raise if foreign."""
    prefix = BASE_NAMESPACE + "/"
    if not isinstance(iri, str) or not iri.startswith(prefix):
        raise ValueError(f"IRI is not under {BASE_NAMESPACE!r}: {iri!r}")
    return iri[len(prefix):]


__all__ = [
    "BASE_NAMESPACE",
    "to_iri",
    "parse_iri",
    "class_iri",
    "predicate_iri",
    "parse_predicate_iri",
    "property_iri",
    "parse_property_iri",
]
