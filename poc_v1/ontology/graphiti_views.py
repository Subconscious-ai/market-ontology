"""Graphiti-compatible views of the canonical NODE_MODELS / EDGE_MODELS.

graphiti-core 0.29's ``add_episode(entity_types=…, edge_types=…,
edge_type_map=…)`` requires Pydantic models that:

1. Do not collide with graphiti's reserved EntityNode / EntityEdge field
   names (``uuid``, ``name``, ``summary``, …) — collision raises
   ``EntityTypeValidationError`` at extraction time.
2. Have no ``Any``-typed fields — OpenAI's structured-output API rejects
   schemas without a concrete ``type`` key, surfacing as an
   ``add_episode`` failure.

This module derives the graphiti view from the canonical schema at
import time. The canonical Pydantic models in ``schema.py`` stay
unchanged — view-models are graphiti-only.

It also builds ``EDGE_TYPE_MAP`` (``dict[(source_label, target_label),
list[predicates]]``) by expanding ``kg_seed_contract.json::edges``.
``from``/``to`` may be a string, a list, or ``"*"`` (wildcard) — the
expander turns all three into concrete ``(from, to)`` cells with the
edge label appended.

Why this lives in market-ontology rather than each consumer:

The graphiti view is a property of the schema (which fields are
exposed for typed extraction), not of any particular consumer. Keeping
it next to the schema means:

- The reserved-field stripping logic stays in lock-step with the
  Pydantic models — adding a new node automatically gets a graphiti
  view, no consumer-side changes needed.
- New consumers (twenty CRM projection, causl.io agent, future research
  bots) import a ready-made view instead of re-deriving it.
- Drift between the contract (``kg_seed_contract.json``) and the model
  registry surfaces at import time in this module rather than at
  add_episode time in production.

Public API:
    ENTITY_TYPES: dict[str, type[BaseModel]]
    EDGE_TYPES:   dict[str, type[BaseModel]]
    EDGE_TYPE_MAP: dict[tuple[str, str], list[str]]
    SCHEMA_VERSION: str
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any, get_args

from pydantic import BaseModel, create_model

from . import schema as _schema

# Field names graphiti-core 0.29 has on its own EntityNode / EntityEdge.
# Custom entity_types / edge_types whose Pydantic fields overlap with
# these will raise EntityTypeValidationError on add_episode (see
# graphiti_core/utils/ontology_utils/entity_types_utils.py:23-37).
# Verified against graphiti-core 0.29; bump these on upgrade.
_GRAPHITI_NODE_RESERVED = frozenset({
    "uuid", "name", "group_id", "labels", "created_at",
    "name_embedding", "summary", "attributes",
})
_GRAPHITI_EDGE_RESERVED = frozenset({
    "uuid", "group_id", "source_node_uuid", "target_node_uuid",
    "created_at", "name", "fact", "fact_embedding", "episodes",
    "expired_at", "valid_at", "invalid_at", "reference_time",
    "attributes",
})


def _annotation_uses_any(annotation: object) -> bool:
    """True if the annotation is ``Any`` or has ``Any`` as a parameter
    (e.g. ``dict[str, Any]``).

    OpenAI's structured-output API requires every field to have a
    concrete JSON schema type, so ``Any``-typed fields trip the LLM with
    ``Invalid schema for response_format X: properties.<field>, schema
    must have a "type" key``. Graphiti surfaces that error as an
    add_episode failure — we drop these fields from the view models
    before passing to entity_types.
    """
    if annotation is Any:
        return True
    args = get_args(annotation)
    return any(a is Any for a in args)


def _strip_reserved(
    canonical: type[BaseModel], reserved: frozenset[str]
) -> type[BaseModel]:
    """Build a graphiti-compatible view of an ontology Pydantic model.

    Drops two kinds of fields:
    1. Names that collide with graphiti-core's reserved Entity / Edge
       attributes (``name``, ``summary``, …).
    2. Fields whose annotation includes ``Any`` (see ``_annotation_uses_any``).

    Every other field — including its ``Field(...)`` default and
    description — is preserved so the LLM still extracts what we care
    about. Canonical Pydantic models in ``schema.py`` stay unchanged.
    """
    fields = {}
    for field_name, field_info in canonical.model_fields.items():
        if field_name in reserved:
            continue
        if _annotation_uses_any(field_info.annotation):
            continue
        fields[field_name] = (field_info.annotation, field_info)
    new_cls = create_model(
        canonical.__name__,
        __doc__=canonical.__doc__,
        **fields,
    )
    new_cls.__module__ = __name__
    return new_cls


ENTITY_TYPES: dict[str, type[BaseModel]] = {
    label: _strip_reserved(model, _GRAPHITI_NODE_RESERVED)
    for label, model in _schema.NODE_MODELS.items()
}
EDGE_TYPES: dict[str, type[BaseModel]] = {
    label: _strip_reserved(model, _GRAPHITI_EDGE_RESERVED)
    for label, model in _schema.EDGE_MODELS.items()
}


def _load_contract() -> dict:
    """Read kg_seed_contract.json from the installed schema package."""
    contract_path = Path(_schema.__file__).parent / "kg_seed_contract.json"
    with contract_path.open() as f:
        return json.load(f)


def _expand_endpoints(endpoint: object, all_node_labels: set[str]) -> list[str]:
    """Turn a contract ``from``/``to`` value into a concrete label list.

    Three accepted shapes:
    - ``"Transition"`` (single label)
    - ``["Transition", "Estimate"]`` (list of labels)
    - ``"*"`` (wildcard — every canonical node)
    """
    if isinstance(endpoint, str):
        if endpoint == "*":
            return sorted(all_node_labels)
        return [endpoint]
    if isinstance(endpoint, list):
        return list(endpoint)
    raise TypeError(
        f"unexpected endpoint shape in kg_seed_contract.json: {endpoint!r}"
    )


def _build_edge_type_map(contract: dict) -> dict[tuple[str, str], list[str]]:
    """Cartesian-product the contract's edges into Graphiti's edge_type_map.

    For each edge label, expand ``from`` and ``to`` to concrete node-label
    lists and add the predicate to every ``(from, to)`` cell. Predicates
    dedupe within a cell so polymorphic edges (``HAS_LEVEL`` via
    Attribute/Trait) don't double-register.
    """
    all_nodes = set(contract["nodes"].keys())
    out: dict[tuple[str, str], list[str]] = {}
    for label, spec in contract["edges"].items():
        from_labels = _expand_endpoints(spec["from"], all_nodes)
        to_labels = _expand_endpoints(spec["to"], all_nodes)
        for f, t in product(from_labels, to_labels):
            cell = out.setdefault((f, t), [])
            if label not in cell:
                cell.append(label)
    return out


_CONTRACT = _load_contract()
EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] = _build_edge_type_map(_CONTRACT)


# Import-time invariant: the contract's node/edge sets must match the
# Pydantic registry. Drift means somebody updated one and not the other —
# regenerate the contract with `python scripts/generate_kg_seed_contract.py`
# and bump SCHEMA_VERSION.
_contract_nodes = set(_CONTRACT["nodes"].keys())
_ontology_nodes = set(ENTITY_TYPES.keys())
if _contract_nodes != _ontology_nodes:
    raise RuntimeError(
        "kg_seed_contract.json drift: "
        f"contract={_contract_nodes} vs ontology={_ontology_nodes}; "
        "regenerate the contract and bump SCHEMA_VERSION."
    )

_contract_edges = set(_CONTRACT["edges"].keys())
_ontology_edges = set(EDGE_TYPES.keys())
if _contract_edges != _ontology_edges:
    raise RuntimeError(
        "kg_seed_contract.json drift: "
        f"contract={_contract_edges} vs ontology={_ontology_edges}; "
        "regenerate the contract and bump SCHEMA_VERSION."
    )

SCHEMA_VERSION = _schema.SCHEMA_VERSION

__all__ = [
    "ENTITY_TYPES",
    "EDGE_TYPES",
    "EDGE_TYPE_MAP",
    "SCHEMA_VERSION",
]
