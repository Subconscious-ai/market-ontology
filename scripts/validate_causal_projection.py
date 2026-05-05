#!/usr/bin/env python3
"""Validate causal DAG projection artifacts.

The JSON Schema checks shape. This script checks the graph semantics JSON
Schema cannot express: known endpoints, role consistency, acyclicity, and
time-series lag rules.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "poc_v1" / "contracts" / "causal_dag_projection.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_json_schema(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    ]


def _variable_errors(projection: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    variables: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for variable in projection.get("variables", []):
        variable_id = variable.get("variable_id")
        if not variable_id:
            continue
        if variable_id in variables:
            errors.append(f"duplicate variable_id: {variable_id}")
        variables[variable_id] = variable

    return variables, errors


def _build_graph(projection: dict[str, Any], variables: dict[str, dict[str, Any]]):
    import networkx as nx

    graph = nx.DiGraph()
    for variable_id, attrs in variables.items():
        graph.add_node(variable_id, **attrs)
    for edge in projection.get("causal_edges", []):
        graph.add_edge(edge["source_variable_id"], edge["target_variable_id"], **edge)
    return graph


def _topological_order(projection: dict[str, Any], variables: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    try:
        import networkx as nx
    except ImportError:
        return _topological_order_without_networkx(projection, variables)

    graph = _build_graph(projection, variables)
    if not nx.is_directed_acyclic_graph(graph):
        try:
            cycle = nx.find_cycle(graph)
            return [], [f"causal_edges contain a cycle: {cycle}"]
        except nx.NetworkXNoCycle:
            return [], ["causal_edges contain a cycle"]
    return list(nx.topological_sort(graph)), []


def _topological_order_without_networkx(
    projection: dict[str, Any],
    variables: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    outgoing: dict[str, list[str]] = {variable_id: [] for variable_id in variables}
    indegree: dict[str, int] = {variable_id: 0 for variable_id in variables}

    for edge in projection.get("causal_edges", []):
        source = edge["source_variable_id"]
        target = edge["target_variable_id"]
        outgoing[source].append(target)
        indegree[target] += 1

    queue = deque(variable_id for variable_id in variables if indegree[variable_id] == 0)
    order: list[str] = []

    while queue:
        variable_id = queue.popleft()
        order.append(variable_id)
        for target in outgoing[variable_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if len(order) != len(variables):
        return [], ["causal_edges contain a cycle"]
    return order, []


def _endpoint_errors(projection: dict[str, Any], variables: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, edge in enumerate(projection.get("causal_edges", [])):
        source = edge.get("source_variable_id")
        target = edge.get("target_variable_id")
        if source not in variables:
            errors.append(f"causal_edges[{index}] unknown source_variable_id: {source}")
        if target not in variables:
            errors.append(f"causal_edges[{index}] unknown target_variable_id: {target}")
    return errors


def _estimation_target_errors(
    projection: dict[str, Any],
    variables: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    target = projection.get("estimation_target", {})

    role_groups = [
        ("Y", [target.get("outcome_variable_id")]),
        ("T", target.get("treatment_variable_ids") or []),
        ("X", target.get("effect_modifier_variable_ids") or []),
        ("W", target.get("control_variable_ids") or []),
    ]
    seen_roles: dict[str, str] = {}

    for expected_role, variable_ids in role_groups:
        for variable_id in variable_ids:
            if not variable_id:
                continue
            previous_role = seen_roles.get(variable_id)
            if previous_role is not None:
                errors.append(
                    f"estimation_target variable {variable_id} has multiple estimation roles: "
                    f"{previous_role} and {expected_role}"
                )
                continue
            seen_roles[variable_id] = expected_role

            variable = variables.get(variable_id)
            if variable is None:
                errors.append(f"estimation_target unknown variable_id: {variable_id}")
                continue
            actual_role = variable.get("estimator_role")
            if actual_role != expected_role:
                errors.append(
                    f"estimation_target variable {variable_id} expected estimator_role "
                    f"{expected_role}, found {actual_role}"
                )

    return errors


def _outcome_errors(
    projection: dict[str, Any],
    variables: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    target = projection.get("estimation_target", {})
    outcome_variable_id = target.get("outcome_variable_id")
    if not outcome_variable_id:
        return errors

    outcome_variable = variables.get(outcome_variable_id)
    if outcome_variable is None:
        return errors

    transition = (projection.get("outcome") or {}).get("transition") or {}
    if transition.get("ontology_node_type") not in (None, "Transition"):
        errors.append("outcome.transition must reference ontology_node_type Transition")
    if outcome_variable.get("ontology_node_type") != "Transition":
        errors.append(
            f"outcome variable {outcome_variable_id} must reference ontology_node_type Transition"
        )
        return errors

    transition_id = transition.get("ontology_node_id")
    if transition_id and outcome_variable.get("ontology_node_id") != transition_id:
        errors.append(
            "outcome.transition ontology_node_id must match estimation_target outcome variable"
        )

    return errors


def _time_series_errors(projection: dict[str, Any]) -> list[str]:
    time_series = projection.get("time_series", {})
    errors: list[str] = []

    if time_series.get("enabled"):
        for field in ("time_index_column", "min_lag", "max_lag"):
            if time_series.get(field) is None:
                errors.append(f"time_series.enabled requires {field}")
        min_lag = time_series.get("min_lag")
        max_lag = time_series.get("max_lag")
        if min_lag is not None and max_lag is not None and min_lag > max_lag:
            errors.append("time_series.min_lag must be <= max_lag")

        for index, edge in enumerate(projection.get("causal_edges", [])):
            lag = edge.get("lag")
            if lag is None:
                errors.append(f"causal_edges[{index}] requires lag when time_series.enabled is true")
                continue
            if min_lag is not None and lag < min_lag:
                errors.append(f"causal_edges[{index}] lag is below min_lag")
            if max_lag is not None and lag > max_lag:
                errors.append(f"causal_edges[{index}] lag is above max_lag")
    else:
        for index, edge in enumerate(projection.get("causal_edges", [])):
            lag = edge.get("lag")
            if lag not in (None, 0):
                errors.append(f"causal_edges[{index}] lag must be null or 0 when time_series is disabled")

    return errors


def validate_projection(projection: dict[str, Any]) -> list[str]:
    errors = validate_json_schema(projection, _load_schema())
    variables, variable_errors = _variable_errors(projection)
    errors.extend(variable_errors)
    errors.extend(_endpoint_errors(projection, variables))
    errors.extend(_estimation_target_errors(projection, variables))
    errors.extend(_outcome_errors(projection, variables))
    errors.extend(_time_series_errors(projection))

    if not errors:
        topological_order, graph_errors = _topological_order(projection, variables)
        errors.extend(graph_errors)
        if topological_order and projection.get("topological_order") not in (None, topological_order):
            errors.append("topological_order does not match causal_edges")

    return errors


def normalize_projection(projection: dict[str, Any]) -> dict[str, Any]:
    errors = validate_projection(projection)
    if errors:
        raise ValueError("; ".join(errors))
    variables, _ = _variable_errors(projection)
    topological_order, graph_errors = _topological_order(projection, variables)
    if graph_errors:
        raise ValueError("; ".join(graph_errors))

    normalized = copy.deepcopy(projection)
    normalized["topological_order"] = topological_order
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projection", help="Path to causal DAG projection JSON")
    args = parser.parse_args(argv)

    try:
        projection = json.loads(Path(args.projection).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        print(f"[causal-projection] ERROR: could not read projection: {exc}", file=sys.stderr)
        return 1

    errors = validate_projection(projection)
    if errors:
        for error in errors:
            print(f"[causal-projection] ERROR: {error}", file=sys.stderr)
        return 1

    print("[causal-projection] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
