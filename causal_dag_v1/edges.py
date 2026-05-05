"""Pydantic edge models for causal_dag_v1.

Four edge types capturing the causal-graph relationships:

  - CAUSES: directed edge from Cause/Intervention → Effect, with
    direction (positive / negative), effect size, CI, and intervention
    semantics (do() vs observe).
  - MEDIATES: Mediator → Effect, attached to the underlying CAUSES edge.
  - MODERATES: Moderator → CAUSES edge, modifies effect_size by a factor.
  - CONFOUNDED_BY: Cause/Effect → Confounder, signals an adjustment need.

Every edge carries the same `start_id` / `end_id` / `properties`
shape used in poc_v1 for direct interop with the kg_seed JSONL writer.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _CausalEdgeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    start_id: str = Field(..., min_length=1)
    end_id: str = Field(..., min_length=1)
    schema_version: str = "1.0.0"


class CAUSES(_CausalEdgeBase):
    """Directed causal edge: start_id (Cause/Intervention) → end_id (Effect/Mediator).

    direction: positive (Cause↑ → Effect↑) or negative (Cause↑ → Effect↓).

    effect_size / ci_low / ci_high: optional. Populated when DCE has
    estimated the effect. None means "hypothesised but unmeasured."

    intervention: 'do' for experimental (Pearl's do-operator), 'observe'
    for observational. Mediation analysis assumes 'observe' upstream
    plus 'do' on the mediator chain.
    """
    direction: Literal["pos", "neg"]
    effect_size: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    intervention: Literal["do", "observe"] = "observe"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MEDIATES(_CausalEdgeBase):
    """Mediator participates in a causal chain. start_id is the Mediator;
    end_id is the Effect at the end of the chain. The full chain
    (Cause → Mediator → Effect) is reconstructed by also looking at the
    CAUSES edges that connect them.
    """
    causes_edge_id: str | None = None  # optional pointer to the CAUSES this mediates


class MODERATES(_CausalEdgeBase):
    """Moderator multiplies / shifts the effect_size of a CAUSES edge.

    start_id is the Moderator. end_id can be either the Effect (shorthand
    for "moderates the cause→effect path leading here") or a synthetic
    edge id when the consumer tracks edges as first-class entities.
    """
    multiplier: float | None = None
    shift: float | None = None


class CONFOUNDED_BY(_CausalEdgeBase):
    """Common-cause edge. start_id is Cause OR Effect, end_id is the
    Confounder. Signals "this Confounder needs to be adjusted for when
    estimating the causal effect."
    """
    adjustment_strategy: Literal[
        "backdoor", "frontdoor", "iv", "regression", "matching", "other"
    ] = "backdoor"


EDGE_MODELS: dict[str, type[_CausalEdgeBase]] = {
    "CAUSES": CAUSES,
    "MEDIATES": MEDIATES,
    "MODERATES": MODERATES,
    "CONFOUNDED_BY": CONFOUNDED_BY,
}
