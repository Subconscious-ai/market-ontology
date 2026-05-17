#!/usr/bin/env python3
"""Generate / check TrustGraph ontology projections.

Derives schema-conformant TrustGraph artifacts from
``poc_v1.ontology.schema`` + ``EDGE_TYPE_MAP``:

* ``trustgraph_ontology.json`` (current projection contract + provenance)
* ``trustgraph_projection.json`` (triple-clean declaration projection)
* ``trustgraph_projection.ttl`` (RDF/Turtle rendering)

All outputs are generated deterministically and support ``--check`` drift
gating in CI.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import sys
import typing
from collections import defaultdict
from enum import Enum
from pathlib import Path

from poc_v1.ontology import iri
from poc_v1.ontology.graphiti_views import EDGE_TYPE_MAP
from poc_v1.ontology.schema import EDGE_MODELS, NODE_MODELS, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent.parent

ONTOLOGY_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_ontology.json"
PROJECTION_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_projection.json"
TTL_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_projection.ttl"

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"

RDF_TYPE = f"{RDF_NS}type"
RDFS_DOMAIN = f"{RDFS_NS}domain"
RDFS_RANGE = f"{RDFS_NS}range"
OWL_CLASS = f"{OWL_NS}Class"
OWL_OBJECT_PROPERTY = f"{OWL_NS}ObjectProperty"
OWL_DATATYPE_PROPERTY = f"{OWL_NS}DatatypeProperty"

LITERAL_EDGE_FIELDS = {"start_id", "end_id", "schema_version", "label"}

# W3C PROV-O mapping for the experiment-lineage layer.
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
        return "object"
    return "string"


def _xsd_for_type(annotation: typing.Any) -> str:
    kind = _type_name(annotation)
    return {
        "boolean": f"{XSD_NS}boolean",
        "integer": f"{XSD_NS}integer",
        "number": f"{XSD_NS}double",
        "date": f"{XSD_NS}date",
        "datetime": f"{XSD_NS}dateTime",
        "string": f"{XSD_NS}string",
        "array": f"{XSD_NS}string",
        "object": f"{XSD_NS}string",
        "string|integer": f"{XSD_NS}string",
    }.get(kind, f"{XSD_NS}string")


def _enum_type(annotation: typing.Any) -> type[Enum] | None:
    origin = typing.get_origin(annotation)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation
    if origin is typing.Union:
        options = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(options) == 1 and isinstance(options[0], type) and issubclass(
            options[0], Enum
        ):
            return options[0]
    return None


def _triple_key(triple: tuple[str, str, str]) -> tuple[str, str, str]:
    return triple


def _edge_property_iri(edge_name: str, field_name: str) -> str:
    return iri.property_iri(f"{edge_name}_{field_name}")


def _build_predicate_maps() -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
]:
    """Build predicate domain/range from EDGE_TYPE_MAP."""
    domain: dict[str, set[str]] = defaultdict(set)
    range_: dict[str, set[str]] = defaultdict(set)
    for (src, tgt), predicates in EDGE_TYPE_MAP.items():
        for predicate_name in predicates:
            domain[predicate_name].add(src)
            range_[predicate_name].add(tgt)

    return domain, range_


def build_projection() -> dict:
    """Build the main TrustGraph projection contract."""
    domain, range_ = _build_predicate_maps()

    classes = []
    triples: set[tuple[str, str, str]] = set()
    axioms: list[dict[str, typing.Any]] = []

    # Aggregate datatype-property metadata so shared names get a stable
    # domain/range across multiple host classes.
    datatype_properties: dict[str, dict[str, typing.Any]] = {}
    for name, model in NODE_MODELS.items():
        class_iri = iri.class_iri(name)
        triples.add((class_iri, RDF_TYPE, OWL_CLASS))
        properties = []
        for field_name, field in model.model_fields.items():
            property_iri = iri.property_iri(field_name)
            properties.append(
                {
                    "name": field_name,
                    "iri": property_iri,
                    "type": _type_name(field.annotation),
                    "required": field.is_required(),
                }
            )

            # Defer per-property schema aggregation to keep shared predicates
            # deterministic and deduplicated in triple output.
            record = datatype_properties.setdefault(
                property_iri,
                {"xsd_ranges": set[str](), "domains": set()},
            )
            record["domains"].add(class_iri)
            record["xsd_ranges"].add(_xsd_for_type(field.annotation))

            if field.is_required():
                axioms.append(
                    {
                        "type": "owl:minCardinality",
                        "subject": class_iri,
                        "predicate": property_iri,
                        "value": 1,
                    }
                )

            enum_type = _enum_type(field.annotation)
            if enum_type is not None:
                axioms.append(
                    {
                        "type": "owl:oneOf",
                        "subject": class_iri,
                        "predicate": property_iri,
                        "values": [item.value for item in enum_type],
                    }
                )

        classes.append(
            {
                "name": name,
                "iri": class_iri,
                "properties": properties,
            }
        )

    predicates = []
    for name in EDGE_MODELS:
        predicate_iri = iri.predicate_iri(name)
        triples.add((predicate_iri, RDF_TYPE, OWL_OBJECT_PROPERTY))
        axioms.append(
            {
                "type": "rdfs:domain",
                "subject": predicate_iri,
                "values": sorted(domain.get(name, set())),
            }
        )
        axioms.append(
            {
                "type": "rdfs:range",
                "subject": predicate_iri,
                "values": sorted(range_.get(name, set())),
            }
        )
        predicates.append(
            {
                "name": name,
                "iri": predicate_iri,
                "domain": sorted(domain.get(name, set())),
                "range": sorted(range_.get(name, set())),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "namespace": iri.BASE_NAMESPACE,
        "generated_from": "poc_v1.ontology.schema",
        "classes": classes,
        "predicates": predicates,
        "datatype_properties": {
            prop: {
                "iri": prop,
                "range": (
                    sorted(data["xsd_ranges"])[0]
                    if len(data["xsd_ranges"]) == 1
                    else f"{XSD_NS}string"
                ),
                "domain": sorted(data["domains"]),
            }
            for prop, data in sorted(datatype_properties.items())
        },
        "prov_o": {
            "classes": PROV_O_CLASSES,
            "predicates": PROV_O_PREDICATES,
        },
        "axioms": axioms,
        "triples": sorted((s, p, o) for s, p, o in triples),
    }


def build_triple_projection() -> dict:
    """Build a flattened triple-clean declaration projection."""
    ontology = build_projection()

    domain, range_ = _build_predicate_maps()
    triple_set: set[tuple[str, str, str]] = set()
    triple_set.update(ontology["triples"])  # type: ignore[arg-type]

    datatype_properties = ontology.get("datatype_properties", {})
    for prop, definition in datatype_properties.items():
        rng = definition["range"]
        for class_iri in definition["domain"]:
            triple_set.add((prop, RDFS_DOMAIN, class_iri))
        triple_set.add((prop, RDFS_RANGE, rng))
        triple_set.add((prop, RDF_TYPE, OWL_DATATYPE_PROPERTY))

    for name in EDGE_MODELS:
        predicate_iri = iri.predicate_iri(name)
        triple_set.add((predicate_iri, RDF_TYPE, OWL_OBJECT_PROPERTY))

        for src in sorted(domain.get(name, set())):
            src_iri = iri.class_iri(src)
            for tgt in sorted(range_.get(name, set())):
                tgt_iri = iri.class_iri(tgt)
                triple_set.add((src_iri, predicate_iri, tgt_iri))
                triple_set.add((predicate_iri, RDFS_DOMAIN, src_iri))
                triple_set.add((predicate_iri, RDFS_RANGE, tgt_iri))

        for field_name, field in EDGE_MODELS[name].model_fields.items():
            if field_name in LITERAL_EDGE_FIELDS:
                continue
            edge_prop_iri = _edge_property_iri(name, field_name)
            rng = _xsd_for_type(field.annotation)
            triple_set.add((edge_prop_iri, RDF_TYPE, OWL_DATATYPE_PROPERTY))
            triple_set.add((edge_prop_iri, RDFS_DOMAIN, predicate_iri))
            triple_set.add((edge_prop_iri, RDFS_RANGE, rng))

    # Deterministic serialization (JSON object ordering and triple sorting).
    triples = [
        {"subject": s, "predicate": p, "object": o}
        for (s, p, o) in sorted(triple_set, key=_triple_key)
    ]
    return {
        "schema_version": ontology["schema_version"],
        "namespace": ontology["namespace"],
        "generated_from": ontology["generated_from"],
        "triples": triples,
    }


def _ttl_term(value: str) -> str:
    return f"<{value}>"


def build_turtle_projection() -> str:
    projection = build_triple_projection()
    lines = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        f"@prefix tg: <{projection['namespace']}/> .",
        "",
        "# TrustGraph triple-clean projection",
        f"# schema_version={projection['schema_version']}",
        "",
    ]
    for triple in projection["triples"]:
        lines.append(
            f"{_ttl_term(triple['subject'])} "
            f"{_ttl_term(triple['predicate'])} "
            f"{_ttl_term(triple['object'])} ."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    ontology = build_projection()
    ontology_text = json.dumps(ontology, indent=2) + "\n"
    projection = build_triple_projection()
    projection_text = json.dumps(projection, indent=2) + "\n"
    ttl_text = build_turtle_projection() + "\n"

    if args.check:
        for path in (ONTOLOGY_PATH, PROJECTION_PATH, TTL_PATH):
            if not path.exists():
                print(f"{path} is missing", file=sys.stderr)
                return 1

        checks = [
            (ONTOLOGY_PATH, ontology_text),
            (PROJECTION_PATH, projection_text),
            (TTL_PATH, ttl_text),
        ]
        for path, current_text in checks:
            current = path.read_text()
            if current != current_text:
                sys.stderr.writelines(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        current_text.splitlines(keepends=True),
                        fromfile=str(path),
                        tofile="generated",
                    )
                )
                return 1
        print(
            "[trustgraph-ontology] OK: "
            f"{ONTOLOGY_PATH}, {PROJECTION_PATH}, {TTL_PATH}"
        )
        return 0

    ONTOLOGY_PATH.write_text(ontology_text)
    PROJECTION_PATH.write_text(projection_text)
    TTL_PATH.write_text(ttl_text)
    print(f"[trustgraph-ontology] wrote {ONTOLOGY_PATH}")
    print(f"[trustgraph-ontology] wrote {PROJECTION_PATH}")
    print(f"[trustgraph-ontology] wrote {TTL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
