"""causal_dag_v1 — peer module to poc_v1 for causal hypothesis DAGs.

Today's poc_v1 is a labeled property graph of *types* (Markets, Stages,
Offerings). Edges express structure (HAS_ATTRIBUTE, FROM, TO).
**This is not a causal DAG.**

causal_dag_v1 is the peer module that holds the *causal* layer:

    NODES: Cause, Effect, Mediator, Moderator, Confounder, Intervention
    EDGES: CAUSES (with direction/sign/effect_size/CI), MEDIATES,
           MODERATES, CONFOUNDED_BY

Lanes feed `poc_v1` (ontology = context). Interview turns and DCE
outputs feed `causal_dag_v1` (causal hypotheses = result).

NetworkX-based acyclicity check enforces "directed acyclic graph"
literally — `validate.is_dag(...)` rejects 3-cycles and self-loops.

DoWhy / EconML / CausalNex are downstream consumers, not schema
definers. This module only provides the Pydantic + NetworkX contract
layer; the DCE engine binds them as needed.
"""

from .nodes import (  # noqa: F401
    Cause,
    Confounder,
    Effect,
    Intervention,
    Mediator,
    Moderator,
    NODE_MODELS,
)
from .edges import (  # noqa: F401
    CAUSES,
    CONFOUNDED_BY,
    EDGE_MODELS,
    MEDIATES,
    MODERATES,
)
from .validate import is_dag, validate_graph  # noqa: F401

CAUSAL_DAG_VERSION = "1.0.0"
