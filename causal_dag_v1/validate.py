"""DAG validator for causal_dag_v1.

Two functions:

  - is_dag(graph): True iff the graph is a directed acyclic graph
    (no cycles, no self-loops).

  - validate_graph(graph): Pydantic-validates every node and edge against
    NODE_MODELS / EDGE_MODELS, then runs is_dag. Returns (errors, ids).

The acyclicity check enforces the "DAG" in causal DAG. Cycles in causal
hypotheses indicate a modeling error — feedback loops need to be
unrolled in time (X_t → Y_t → X_{t+1}) or factored through Mediators.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from .edges import EDGE_MODELS
from .nodes import NODE_MODELS


def is_dag(graph: dict[str, Any]) -> bool:
    """True iff the directed graph is acyclic AND has no self-loops.

    `graph` is the canonical {"nodes": {label: [...]}, "edges": {label: [...]}}
    shape. Only CAUSES and MEDIATES edges contribute to the directed
    structure (MODERATES and CONFOUNDED_BY are annotations on the
    causal chain, not part of it).
    """
    nodes_section = graph.get("nodes") or {}
    edges_section = graph.get("edges") or {}

    nodes: set[str] = set()
    adjacency: dict[str, set[str]] = {}
    indegree: dict[str, int] = {}

    def _add_node(node_id: str) -> None:
        if node_id in nodes:
            return
        nodes.add(node_id)
        adjacency.setdefault(node_id, set())
        indegree.setdefault(node_id, 0)

    def _add_edge(start: str, end: str) -> None:
        _add_node(start)
        _add_node(end)
        if end in adjacency[start]:
            return
        adjacency[start].add(end)
        indegree[end] += 1

    for rows in nodes_section.values():
        for row in rows:
            node_id = row.get("id")
            if node_id:
                _add_node(node_id)

    for label in ("CAUSES", "MEDIATES"):
        for e in edges_section.get(label) or []:
            start = e.get("start_id")
            end = e.get("end_id")
            if start and end:
                if start == end:
                    return False  # self-loops are not DAGs
                _add_edge(start, end)

    # Kahn's algorithm for cycle detection.
    queue = deque([n for n in nodes if indegree.get(n, 0) == 0])
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for nbr in adjacency.get(node, ()):
            indegree[nbr] -= 1
            if indegree[nbr] == 0:
                queue.append(nbr)

    return visited == len(nodes)


def validate_graph(graph: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    """Pydantic-validate every node + edge, then check is_dag.

    Returns (errors, ids):
      errors: list of human-readable validation failure strings (empty on success)
      ids: {"nodes": [...], "edges": [...]} — the IDs that validated OK
    """
    errors: list[str] = []
    valid_node_ids: list[str] = []
    valid_edge_keys: list[str] = []

    nodes_section = graph.get("nodes") or {}
    edges_section = graph.get("edges") or {}

    for label, rows in nodes_section.items():
        model = NODE_MODELS.get(label)
        if model is None:
            errors.append(f"unknown node label {label!r}")
            continue
        for i, row in enumerate(rows):
            nid = row.get("id")
            props = row.get("properties") or {}
            if not nid:
                errors.append(f"{label}[{i}] missing id")
                continue
            try:
                model.model_validate(props)
                valid_node_ids.append(nid)
            except Exception as e:  # noqa: BLE001 — Pydantic raises ValidationError
                errors.append(f"{label}[{nid}] invalid: {e}")

    for label, rows in edges_section.items():
        model = EDGE_MODELS.get(label)
        if model is None:
            errors.append(f"unknown edge label {label!r}")
            continue
        for i, row in enumerate(rows):
            try:
                payload = {
                    "start_id": row.get("start_id"),
                    "end_id": row.get("end_id"),
                    **(row.get("properties") or {}),
                }
                model.model_validate(payload)
                valid_edge_keys.append(
                    f"{label}::{row.get('start_id')}->{row.get('end_id')}"
                )
            except Exception as e:  # noqa: BLE001
                errors.append(f"{label}[{i}] invalid: {e}")

    if not is_dag(graph):
        errors.append("graph contains a cycle or self-loop in CAUSES/MEDIATES")

    return errors, {"nodes": valid_node_ids, "edges": valid_edge_keys}
