"""
v1 POC ontology — Pydantic models for write-boundary validation.

Every node or edge written to the property graph must first validate through these models.
This is the single source of truth for the schema. Keep it aligned with:
  - ontology/node_schemas.json
  - ontology/edge_schemas.json
  - graph-store adapter constraints/import scripts

Schema version: 1.5.0
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.5.0"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ArchetypeType(str, Enum):
    CUSTOMER = "customer"
    COMPETITOR_BUYER = "competitor_buyer"
    COMPETITOR_USER = "competitor_user"


class EvidenceSourceType(str, Enum):
    S1 = "s1"
    TEN_K = "10k"
    INTERVIEW = "interview"
    SURVEY = "survey"
    BENCHMARK = "benchmark"
    WEB = "web"
    DECK = "deck"
    EXECUTIVE_INTERVIEW = "executive_interview"
    RESEARCH_AGENT = "research_agent"


class EvidenceSignalType(str, Enum):
    METRIC = "metric"
    OBSERVATION = "observation"
    RECOMMENDATION = "recommendation"
    OBJECTIVE = "objective"
    QUESTION = "question"


class AttributeDataType(str, Enum):
    CONTINUOUS = "continuous"
    ORDINAL = "ordinal"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class EstimateType(str, Enum):
    PART_WORTH = "part_worth"
    TRANSITION_PROBABILITY = "transition_probability"
    WTP = "wtp"
    ELASTICITY = "elasticity"
    ATE = "ate"
    AMCE = "amce"
    IMPORTANCE = "importance"


class ExperimentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Common mixins
# ---------------------------------------------------------------------------

class _VersionedNode(BaseModel):
    schema_version: str = SCHEMA_VERSION
    ingested_at: Optional[datetime] = None


class _TemporallyValid(BaseModel):
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    @model_validator(mode="after")
    def _check_range(self):
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be <= valid_to")
        return self


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

class Market(_VersionedNode):
    """Scope boundary for every query. One market per ontology in v1."""
    id: str
    name: str
    definition: str
    geography: Optional[str] = None
    industry_codes: list[str] = Field(default_factory=list)
    # Context factors folded in as flexible props for v1.
    # In v2, these become first-class ContextFactor nodes.
    context_factors: dict[str, Any] = Field(default_factory=dict)
    period: Optional[str] = None


class Stage(_VersionedNode):
    """A discrete step in a buyer's decision journey through a Market.

    `name` is a free string: funnels vary by market. AARRR pirate metrics
    (awareness, acquisition, activation, retention, referral, revenue),
    SaaS trial funnels, and retail purchase journeys are all valid — the
    schema does not enforce one company's funnel taxonomy on every market.
    """
    id: str
    name: str
    definition: str


class Transition(_VersionedNode):
    id: str
    name: str
    from_stage_id: str
    to_stage_id: str
    definition: str


class StakeholderArchetype(_VersionedNode):
    """A type of buyer, user, or decision-maker whose preferences shape a
    Market. The persona's traits are the HAS_TRAIT edge graph
    (StakeholderArchetype -[:HAS_TRAIT]-> Trait -[:HAS_LEVEL]-> TraitLevel) —
    there is no denormalized `traits` dict (removed in v1.5)."""
    id: str
    name: str
    archetype_type: ArchetypeType
    role: Optional[str] = None
    segment: Optional[str] = None
    industry: Optional[str] = None
    company_size_band: Optional[str] = None
    definition: Optional[str] = None


class Offering(_VersionedNode):
    """A specific product or service a Company brings to a Market.

    The owning company is the OFFERED_BY edge to a Company node. The
    `company_name` string prop was removed in v1.5 — the Company node is
    the single source of truth (populated from spice-harvester research)."""
    id: str
    name: str
    is_competitor: bool = False
    category: Optional[str] = None
    definition: Optional[str] = None


class Company(_VersionedNode):
    """The organization that offers one or more Offerings. Added in v1.1 to
    give Offering→Company a proper edge for rollup queries. Minimal props;
    add funding/size/industry in a later bump when a consumer needs them."""
    id: str
    name: str
    domain: Optional[str] = None
    definition: Optional[str] = None


class Attribute(_VersionedNode):
    """A dimension of an Offering that can be varied in an experiment."""
    id: str
    name: str
    data_type: AttributeDataType
    unit: Optional[str] = None
    definition: str
    # Subconscious API typically populates this.


class AttributeLevel(_VersionedNode, _TemporallyValid):
    """A plausible level for an Attribute in a Market/period.

    `value` is a typed JSON scalar (the concrete level — e.g. 1499,
    "premium", True). Typed rather than `Any` so it survives the typed
    graph projections; interpret it against the parent Attribute's
    `data_type`. Typically populated from Rehoboam's
    get_attributes_levels APIs.
    """
    id: str
    attribute_id: str
    market_id: str
    value: bool | int | float | str
    label: Optional[str] = None
    is_status_quo: bool = False


class Trait(_VersionedNode):
    """A dimension of a StakeholderArchetype used to describe a persona."""
    id: str
    name: str
    data_type: AttributeDataType
    unit: Optional[str] = None
    definition: str


class TraitLevel(_VersionedNode, _TemporallyValid):
    """A plausible value for a Trait in a Market/period.

    `value` is a typed JSON scalar; interpret it against the parent
    Trait's `data_type`. See `AttributeLevel.value`.
    """
    id: str
    trait_id: str
    market_id: str
    value: bool | int | float | str
    label: Optional[str] = None
    is_status_quo: bool = False


class Need(_VersionedNode):
    """An outcome a StakeholderArchetype is trying to achieve in a Market —
    the job-to-be-done behind a Transition.

    Attributes matter only insofar as they ADDRESS a Need; archetypes
    HAS_NEED the outcomes that drive their decisions. Modeling the Need
    explicitly makes a measured attribute importance *explainable* (which
    buyer outcome it serves) rather than merely a number.
    """
    id: str
    name: str
    definition: str


class Evidence(_VersionedNode):
    id: str
    source_type: EvidenceSourceType
    source_ref: str  # e.g. "sec://company-x/s1/2026-02-14"
    source_url: Optional[str] = None
    excerpt: Optional[str] = None
    extracted_claim: Optional[str] = None  # structured claim, not prose
    retrieval_query: Optional[str] = None
    extractor_version: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    signal_type: Optional[EvidenceSignalType] = None
    period_observed: Optional[str] = None


class Estimate(_VersionedNode, _TemporallyValid):
    """Results returned from Subconscious experiments."""
    id: str
    estimate_type: EstimateType
    value: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    standard_error: Optional[float] = None
    subconscious_experiment_id: str
    model_version: str
    ontology_snapshot_hash: str
    estimated_at: datetime


class WandbArtifactRef(BaseModel):
    entity: str
    project: str
    run_id: Optional[str] = None
    name: str
    type: str
    version: str
    digest: str
    qualified_name: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    files: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentRun(_VersionedNode):
    """Experiment execution record tying a snapshot to SuperEgo/W&B artifacts."""
    id: str
    ontology_snapshot_hash: str
    super_ego_run_id: Optional[str] = None
    wandb_entity: Optional[str] = None
    wandb_project: Optional[str] = None
    wandb_run_id: Optional[str] = None
    wandb_run_name: Optional[str] = None
    status: ExperimentRunStatus
    artifact_refs: list[str] = Field(default_factory=list)
    wandb_artifacts: list[WandbArtifactRef] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)
    sample_size: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _check_run_time_range(self):
        if self.started_at and self.completed_at and self.started_at > self.completed_at:
            raise ValueError("started_at must be <= completed_at")
        return self


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

class _Edge(BaseModel):
    start_id: str
    end_id: str
    schema_version: str = SCHEMA_VERSION


class EdgeFrom(_Edge):
    """Transition -[:FROM]-> Stage"""
    label: Literal["FROM"] = "FROM"


class EdgeTo(_Edge):
    """Transition -[:TO]-> Stage"""
    label: Literal["TO"] = "TO"


class EdgeInMarket(_Edge):
    """Transition -[:IN_MARKET]-> Market"""
    label: Literal["IN_MARKET"] = "IN_MARKET"


class EdgeRelevantTo(_Edge):
    """Transition -[:RELEVANT_TO]-> StakeholderArchetype"""
    label: Literal["RELEVANT_TO"] = "RELEVANT_TO"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EdgeAbout(_Edge):
    """Transition -[:ABOUT]-> Offering, or Estimate -[:ABOUT]-> any node."""
    label: Literal["ABOUT"] = "ABOUT"
    target_node_type: Optional[str] = None  # for Estimate-ABOUT polymorphism


class EdgeHasAttribute(_Edge):
    """Offering -[:HAS_ATTRIBUTE]-> Attribute"""
    label: Literal["HAS_ATTRIBUTE"] = "HAS_ATTRIBUTE"


class EdgeHasLevel(_Edge):
    """Attribute/Trait -[:HAS_LEVEL]-> AttributeLevel/TraitLevel"""
    label: Literal["HAS_LEVEL"] = "HAS_LEVEL"


class EdgeHasTrait(_Edge):
    """StakeholderArchetype -[:HAS_TRAIT]-> Trait"""
    label: Literal["HAS_TRAIT"] = "HAS_TRAIT"


class EdgeRelevantAt(_Edge, _TemporallyValid):
    """Attribute -[:RELEVANT_AT]-> Stage.

    Temporal relevance score for which AARRR stages an attribute matters at.
    """
    label: Literal["RELEVANT_AT"] = "RELEVANT_AT"
    score: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class EdgeSupports(_Edge):
    """Evidence -[:SUPPORTS]-> any node."""
    label: Literal["SUPPORTS"] = "SUPPORTS"
    target_node_type: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    support_type: Optional[str] = None  # "direct" | "benchmark" | "inferred"


class EdgeOfferedBy(_Edge):
    """Offering -[:OFFERED_BY]-> Company. Introduced in v1.1 as the
    programmatic rollup link. Consumers aggregating Attributes/Levels up
    to the Company level traverse this edge."""
    label: Literal["OFFERED_BY"] = "OFFERED_BY"


class EdgeCompetesWith(_Edge):
    """Offering -[:COMPETES_WITH]-> Offering."""
    label: Literal["COMPETES_WITH"] = "COMPETES_WITH"


class EdgeOfferingInMarket(_Edge):
    """Offering -[:OFFERING_IN_MARKET]-> Market.

    Kept distinct from Transition -[:IN_MARKET]-> Market because the
    TrustGraph projection has one domain/range pair per property.
    """
    label: Literal["OFFERING_IN_MARKET"] = "OFFERING_IN_MARKET"


class EdgeTargetsStakeholder(_Edge):
    """Offering -[:TARGETS_STAKEHOLDER]-> StakeholderArchetype."""
    label: Literal["TARGETS_STAKEHOLDER"] = "TARGETS_STAKEHOLDER"


class EdgeConsumed(_Edge):
    """ExperimentRun -[:CONSUMED]-> any ontology context node."""
    label: Literal["CONSUMED"] = "CONSUMED"
    target_node_type: Optional[str] = None


class EdgeProduced(_Edge):
    """ExperimentRun -[:PRODUCED]-> Estimate."""
    label: Literal["PRODUCED"] = "PRODUCED"


class EdgeAddresses(_Edge):
    """Attribute -[:ADDRESSES]-> Need.

    The attribute is a lever on the buyer outcome. This is the
    explainability link: a measured attribute importance traces back to
    the Need it serves.
    """
    label: Literal["ADDRESSES"] = "ADDRESSES"


class EdgeHasNeed(_Edge):
    """StakeholderArchetype -[:HAS_NEED]-> Need."""
    label: Literal["HAS_NEED"] = "HAS_NEED"


# ---------------------------------------------------------------------------
# Convenience: registry for writers/importers
# ---------------------------------------------------------------------------

NODE_MODELS: dict[str, type[BaseModel]] = {
    "Market": Market,
    "Stage": Stage,
    "Transition": Transition,
    "StakeholderArchetype": StakeholderArchetype,
    "Offering": Offering,
    "Attribute": Attribute,
    "AttributeLevel": AttributeLevel,
    "Trait": Trait,
    "TraitLevel": TraitLevel,
    "Need": Need,
    "Evidence": Evidence,
    "Estimate": Estimate,
    "Company": Company,
    "ExperimentRun": ExperimentRun,
}

EDGE_MODELS: dict[str, type[BaseModel]] = {
    "FROM": EdgeFrom,
    "TO": EdgeTo,
    "IN_MARKET": EdgeInMarket,
    "RELEVANT_TO": EdgeRelevantTo,
    "ABOUT": EdgeAbout,
    "HAS_ATTRIBUTE": EdgeHasAttribute,
    "HAS_LEVEL": EdgeHasLevel,
    "HAS_TRAIT": EdgeHasTrait,
    "RELEVANT_AT": EdgeRelevantAt,
    "SUPPORTS": EdgeSupports,
    "ADDRESSES": EdgeAddresses,
    "HAS_NEED": EdgeHasNeed,
    "OFFERED_BY": EdgeOfferedBy,
    "COMPETES_WITH": EdgeCompetesWith,
    "OFFERING_IN_MARKET": EdgeOfferingInMarket,
    "TARGETS_STAKEHOLDER": EdgeTargetsStakeholder,
    "CONSUMED": EdgeConsumed,
    "PRODUCED": EdgeProduced,
}


def validate_node(label: str, payload: dict) -> BaseModel:
    model = NODE_MODELS.get(label)
    if model is None:
        raise ValueError(f"Unknown node label: {label}")
    return model(**payload)


def validate_edge(label: str, payload: dict) -> BaseModel:
    model = EDGE_MODELS.get(label)
    if model is None:
        raise ValueError(f"Unknown edge label: {label}")
    return model(**payload)
