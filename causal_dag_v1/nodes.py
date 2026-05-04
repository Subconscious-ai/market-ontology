"""Pydantic node models for causal_dag_v1.

Six node types covering hypothesis-first causal modeling:

  - Cause: an antecedent variable (could be Intervention or just Observed)
  - Effect: a consequence variable
  - Mediator: an intermediate causal variable on a Cause→Effect path
  - Moderator: context that modulates Cause→Effect strength
  - Confounder: common cause of Cause and Effect needing adjustment
  - Intervention: a `do()`-style manipulable variable

Every node has a stable `id`, a human-readable `name`, an optional
`description`, an optional source `evidence_id` (links to a poc_v1
Evidence node — the cross-module bridge), and a confidence score.

Provenance is enforced at the schema layer: every causal node carries
`source: Literal["interview", "dce", "expert", "literature"]` so
consumers can filter / weight by source class.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Bridge type — Causal nodes can reference Evidence and Estimate ids
# from poc_v1 (the structural ontology). The string form keeps this
# module decoupled — no import from poc_v1 needed.
PocV1Id = str


class _CausalNodeBase(BaseModel):
    """Shared fields for all causal_dag_v1 nodes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=240)
    description: str | None = Field(None, max_length=2000)
    source: Literal["interview", "dce", "expert", "literature"] = "interview"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_ids: list[PocV1Id] = Field(default_factory=list)
    schema_version: str = "1.0.0"


class Cause(_CausalNodeBase):
    """An antecedent variable. May be an Intervention (manipulable) or
    Observed (passive).
    """
    manipulable: bool = False


class Effect(_CausalNodeBase):
    """A consequence variable. Can have an attached metric — what would
    the DCE engine *measure* to estimate this effect?
    """
    metric: str | None = Field(None, max_length=120)


class Mediator(_CausalNodeBase):
    """An intermediate causal variable on a Cause → Effect path.
    Used in mediation analysis (Baron & Kenny, modern direct/indirect
    effect decomposition).
    """


class Moderator(_CausalNodeBase):
    """Context that modulates the strength of a Cause → Effect link.
    Different from Mediator: a moderator sits *outside* the causal chain
    but changes the chain's coefficient.
    """


class Confounder(_CausalNodeBase):
    """A common cause of both Cause and Effect. Needs to be adjusted for
    when estimating the causal effect (backdoor adjustment).
    """


class Intervention(_CausalNodeBase):
    """A `do()`-style manipulable variable. Distinct from Cause because
    Intervention is by design controllable in an experiment; Cause is
    a hypothesis that *could* be intervened on.
    """
    intervention_type: Literal["binary", "continuous", "categorical"] = "binary"
    levels: list[str] = Field(default_factory=list)


NODE_MODELS: dict[str, type[_CausalNodeBase]] = {
    "Cause": Cause,
    "Effect": Effect,
    "Mediator": Mediator,
    "Moderator": Moderator,
    "Confounder": Confounder,
    "Intervention": Intervention,
}
