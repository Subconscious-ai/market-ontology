#!/usr/bin/env python3
"""
Validate every JSONL fixture under poc_v1/kg_seed/ against the Pydantic
schema in poc_v1/ontology/schema.py. Exits non-zero on any failure.

This is the primary CI check — when the schema changes, fixtures drift,
or a new node/edge type lands, this catches the mismatch before downstream
consumers (spice-harvester, ai-chatbot) silently break.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "poc_v1" / "ontology" / "schema.py"
KG_SEED_DIR = ROOT / "poc_v1" / "kg_seed"


def load_schema():
    spec = importlib.util.spec_from_file_location("schema", SCHEMA_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["schema"] = mod
    spec.loader.exec_module(mod)
    for reg in (getattr(mod, "NODE_MODELS", {}), getattr(mod, "EDGE_MODELS", {})):
        for cls in reg.values():
            try:
                cls.model_rebuild(_types_namespace={**vars(mod)})
            except Exception:
                pass
    return mod.validate_node, mod.validate_edge


# Filename → (label, is_edge)
FIXTURES = {
    "markets.jsonl":                       ("Market", False),
    "stages.jsonl":                        ("Stage", False),
    "transitions.jsonl":                   ("Transition", False),
    "stakeholder_archetypes.jsonl":        ("StakeholderArchetype", False),
    "offerings.jsonl":                     ("Offering", False),
    "attributes.jsonl":                    ("Attribute", False),
    "attribute_levels.jsonl":              ("AttributeLevel", False),
    "evidence.jsonl":                      ("Evidence", False),
    "estimates.jsonl":                     ("Estimate", False),
    "edges_transition_from_stage.jsonl":   ("FROM", True),
    "edges_transition_to_stage.jsonl":     ("TO", True),
    "edges_transition_in_market.jsonl":    ("IN_MARKET", True),
    "edges_transition_relevant_to.jsonl":  ("RELEVANT_TO", True),
    "edges_transition_about_offering.jsonl": ("ABOUT", True),
    "edges_estimate_about.jsonl":          ("ABOUT", True),
    "edges_offering_has_attribute.jsonl":  ("HAS_ATTRIBUTE", True),
    "edges_attribute_has_level.jsonl":     ("HAS_LEVEL", True),
    "edges_attribute_relevant_at.jsonl":   ("RELEVANT_AT", True),
    "edges_evidence_supports.jsonl":       ("SUPPORTS", True),
}


def main() -> int:
    validate_node, validate_edge = load_schema()
    errors: list[str] = []
    checked = 0

    # Catch new fixture files that haven't been mapped to a model yet.
    on_disk = {p.name for p in KG_SEED_DIR.glob("*.jsonl")}
    unmapped = sorted(on_disk - set(FIXTURES))
    if unmapped:
        errors.append(
            f"kg_seed/ has unmapped fixture file(s): {unmapped}. "
            "Add them to FIXTURES in scripts/validate_kg_seed.py."
        )

    for fname, (label, is_edge) in FIXTURES.items():
        path = KG_SEED_DIR / fname
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{fname}:{lineno}: invalid JSON — {e}")
                continue
            try:
                props = dict(rec.get("properties", {}))
                if is_edge:
                    payload = {**props, "start_id": rec["start_id"], "end_id": rec["end_id"]}
                    validate_edge(label, payload)
                else:
                    payload = {**props, "id": rec["id"]}
                    validate_node(label, payload)
                checked += 1
            except Exception as e:
                errors.append(f"{fname}:{lineno}: {label} validation — {e}")

    print(f"[validate-kg-seed] checked {checked} records across {len(FIXTURES)} fixture files")

    if errors:
        print(f"\n[validate-kg-seed] FAILED — {len(errors)} error(s):", file=sys.stderr)
        for err in errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  … and {len(errors) - 50} more", file=sys.stderr)
        return 1

    print("[validate-kg-seed] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
