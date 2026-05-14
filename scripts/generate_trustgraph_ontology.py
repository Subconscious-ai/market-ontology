#!/usr/bin/env python3
"""Generate/check the TrustGraph Ontology RAG projection."""

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_v1.ontology import schema  # noqa: E402

PROJECTION_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_projection.json"
ONTOLOGY_PATH = ROOT / "poc_v1" / "ontology" / "trustgraph_ontology.json"


def load_projection() -> dict[str, Any]:
    return json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))


def _label(value: str) -> list[dict[str, str]]:
    return [{"value": value, "lang": "en"}]


def _assert_edge_coverage(projection: dict[str, Any]) -> None:
    seen = {}
    for prop_id, spec in projection["objectProperties"].items():
        edge_label = spec["edgeLabel"]
        if edge_label in seen:
            raise SystemExit(
                f"edge label {edge_label} mapped by both {seen[edge_label]} and {prop_id}"
            )
        seen[edge_label] = prop_id
    expected = set(schema.EDGE_MODELS)
    actual = set(seen)
    if expected != actual:
        raise SystemExit(
            "TrustGraph object property drift: "
            f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def _assert_class_coverage(projection: dict[str, Any]) -> None:
    """Every entity in schema.NODE_MODELS must have a class-level spec
    (label + comment) in projection["classes"]. Adding/removing a Pydantic
    model forces a corresponding projection update — fail loud here so
    drift can't ship silently."""
    expected = set(schema.NODE_MODELS)
    actual = set(projection.get("classes", {}))
    if expected != actual:
        raise SystemExit(
            "TrustGraph class projection drift: "
            f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def _object_property(namespace: str, prop_id: str, spec: dict[str, Any], class_ids: set[str]) -> dict[str, Any]:
    out = {
        "uri": f"{namespace}{prop_id}",
        "type": "owl:ObjectProperty",
        "rdfs:label": _label(spec["label"]),
        "rdfs:comment": spec["comment"],
    }
    for key, rdf_key in (("domain", "rdfs:domain"), ("range", "rdfs:range")):
        value = spec.get(key)
        if not value:
            continue
        if value not in class_ids:
            raise SystemExit(f"{prop_id}: unknown {key} {value}")
        out[rdf_key] = value
    return out


def _datatype_property(namespace: str, prop_id: str, spec: dict[str, Any], class_ids: set[str]) -> dict[str, Any]:
    out = {
        "uri": f"{namespace}{prop_id}",
        "type": "owl:DatatypeProperty",
        "rdfs:label": _label(spec["label"]),
        "rdfs:comment": spec.get(
            "comment",
            f"Extraction property for canonical field {spec['field']}.",
        ),
        "rdfs:range": spec["range"],
    }
    domain = spec.get("domain")
    if domain:
        if domain not in class_ids:
            raise SystemExit(f"{prop_id}: unknown domain {domain}")
        out["rdfs:domain"] = domain
    return out


def build_ontology() -> dict[str, Any]:
    projection = load_projection()
    _assert_edge_coverage(projection)
    _assert_class_coverage(projection)
    namespace = projection["namespace"]
    root = projection["rootClass"]
    root_id = root["id"]
    classes = {
        root_id: {
            "uri": f"{namespace}{root_id}",
            "type": "owl:Class",
            "rdfs:label": _label(root["label"]),
            "rdfs:comment": root["comment"],
            "dcterms:identifier": root_id,
        }
    }
    for label in schema.NODE_MODELS:
        cls_spec = projection["classes"][label]
        classes[label] = {
            "uri": f"{namespace}{label}",
            "type": "owl:Class",
            "rdfs:label": _label(cls_spec.get("label", label)),
            "rdfs:comment": cls_spec["comment"],
            "rdfs:subClassOf": root_id,
            "dcterms:identifier": label,
        }

    object_properties = {
        prop_id: _object_property(namespace, prop_id, spec, set(classes))
        for prop_id, spec in projection["objectProperties"].items()
    }
    datatype_properties = {
        prop_id: _datatype_property(namespace, prop_id, spec, set(classes))
        for prop_id, spec in projection["datatypeProperties"].items()
    }
    return {
        "metadata": {
            "id": projection["ontologyId"],
            "name": projection["name"],
            "namespace": namespace,
            "description": projection["description"],
            "schemaVersion": schema.SCHEMA_VERSION,
            "projectionVersion": projection["projectionVersion"],
        },
        "classes": classes,
        "objectProperties": object_properties,
        "datatypeProperties": datatype_properties,
    }


def render_ontology(ontology: dict[str, Any]) -> str:
    return json.dumps(ontology, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render_ontology(build_ontology())
    if not args.check:
        ONTOLOGY_PATH.write_text(text, encoding="utf-8")
        print(f"[trustgraph-ontology] wrote {ONTOLOGY_PATH}")
        return 0
    if not ONTOLOGY_PATH.exists():
        print(f"{ONTOLOGY_PATH} is missing", file=sys.stderr)
        return 1
    current = ONTOLOGY_PATH.read_text(encoding="utf-8")
    if current == text:
        print(f"[trustgraph-ontology] OK: {ONTOLOGY_PATH}")
        return 0
    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        text.splitlines(keepends=True),
        fromfile=str(ONTOLOGY_PATH),
        tofile="generated",
    )
    sys.stderr.writelines(diff)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
