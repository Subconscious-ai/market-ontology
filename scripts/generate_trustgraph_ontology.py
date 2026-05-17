#!/usr/bin/env python3
"""Generate / check the TrustGraph ontology projection.

Derives a TrustGraph-conformant projection of the canonical ontology
(`poc_v1.ontology.schema`) — classes, predicates, and the W3C PROV-O
lineage mapping — entirely from `NODE_MODELS` / `EDGE_MODELS` plus the
canonical IRI scheme. Because every line is derived, the projection
cannot drift from the schema; the `--check` mode gates that in CI.

Scope (issue #71): this is the *minimal conformance projection*. It
carries class IRIs, property types + required-ness (the lightweight
cardinality signal), predicate domain/range, and the PROV-O mapping.
Formal OWL axiom serialization and triple-clean RDF/Turtle output are
deliberately deferred until a TrustGraph backend consumes this artifact
— TrustGraph is a conformance target we project toward, not a backend
we migrate to (umbrella #70). See `docs/PROV-O.md`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import sys
import typing
from enum import Enum
from pathlib import Path

from poc_v1.ontology import iri
from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP
from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS, SCHEMA_VERSION

OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "poc_v1"
    / "ontology"
    / "trustgraph_ontology.json"
)

# W3C PROV-O mapping for the experiment-lineage layer. This is the one
# hand-authored part of the projection — the lineage contract. Documented
# in docs/PROV-O.md; every term traces to an existing schema field.
PROV_O_CLASSES = {
    "ExperimentRun": "prov:Activity",
    "Estimate": "prov:Entity",
    "Evidence": "prov:Entity",
}
PROV_O_PREDICATES = {
    "CONSUMED": "prov:used",
    "PRODUCED": "prov:wasGeneratedBy",
    "SUPPORTS": "prov:wasDerivedFrom",
}


def _type_name(annotation: typing.Any) -> str:
    """Map a Pydantic field annotation to a projection type token."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _type_name(args[0])
        return "|".join(_type_name(a) for a in args)
    if origin in (list, set, tuple):
        return "array"
    if origin is dict:
        return "object"
    if isinstance(annotation, type):
        if issubclass(annotation, Enum):
            return "string"
        if issubclass(annotation, bool):
            return "boolean"
        if issubclass(annotation, int):
            return "integer"
        if issubclass(annotation, float):
            return "number"
        if issubclass(annotation, str):
            return "string"
        if issubclass(annotation, _dt.datetime):
            return "datetime"
        if issubclass(annotation, _dt.date):
            return "date"
        return "object"  # nested BaseModel
    return "string"


def build_projection() -> dict:
    """Build the TrustGraph projection from the canonical schema."""
    classes = []
    for name, model in NODE_MODELS.items():
        properties = [
            {
                "name": field_name,
                "iri": iri.property_iri(field_name),
                "type": _type_name(field.annotation),
                "required": field.is_required(),
            }
            for field_name, field in model.model_fields.items()
        ]
        classes.append(
            {"name": name, "iri": iri.class_iri(name), "properties": properties}
        )

    # Predicate domain/range from the graphiti EDGE_TYPE_MAP — the declared
    # (source, target) pairs each edge label connects.
    domain: dict[str, set[str]] = {}
    range_: dict[str, set[str]] = {}
    for (src, tgt), preds in EDGE_TYPE_MAP.items():
        for predicate in preds:
            domain.setdefault(predicate, set()).add(src)
            range_.setdefault(predicate, set()).add(tgt)

    predicates = [
        {
            "name": name,
            "iri": iri.predicate_iri(name),
            "domain": sorted(domain.get(name, set())),
            "range": sorted(range_.get(name, set())),
        }
        for name in EDGE_MODELS
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "namespace": iri.BASE_NAMESPACE,
        "generated_from": "poc_v1.ontology.schema",
        "classes": classes,
        "predicates": predicates,
        "prov_o": {
            "classes": PROV_O_CLASSES,
            "predicates": PROV_O_PREDICATES,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    text = json.dumps(build_projection(), indent=2) + "\n"

    if args.check:
        if not OUT_PATH.exists():
            print(f"{OUT_PATH} is missing", file=sys.stderr)
            return 1
        current = OUT_PATH.read_text()
        if current != text:
            sys.stderr.writelines(
                difflib.unified_diff(
                    current.splitlines(keepends=True),
                    text.splitlines(keepends=True),
                    fromfile=str(OUT_PATH),
                    tofile="generated",
                )
            )
            return 1
        print(f"[trustgraph-ontology] OK: {OUT_PATH}")
        return 0

    OUT_PATH.write_text(text)
    print(f"[trustgraph-ontology] wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
