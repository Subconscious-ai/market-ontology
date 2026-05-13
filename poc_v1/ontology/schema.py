"""
v1 POC ontology — Pydantic models for write-boundary validation.

Every node or edge written to the property graph must first validate through these models.
This is the single source of truth for the schema. Keep it aligned with:
  - ontology/node_schemas.json
  - ontology/edge_schemas.json
  - graph-store adapter constraints/import scripts

Schema version: 1.4.0 — see MIGRATION.md for what changed from 1.3.1.

v1.4.0 adds Continuant-to-Continuant primitives (competesWith, partneredWith,
acquired, producedBy, alternativeTo, complementOf, plays) and a new Person
sortal that plays the StakeholderArchetype role. Motivated by the substrate
hygiene diagnostic in sizzl-trustgraph#181: extraction logs show the LLM
naturally emits competesWith / competitorOf / partnersWith / alternativeTo /
acquired ~136 times across 423 chunks, all dropped by the validator because
these predicates were not declared.

Backwards-compatible: all v1.3.1 data validates against v1.4.0 unchanged.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.4.0"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StageName(str, Enum):
    AWARENESS = "awareness"
    ACQUISITION = "acquisition"
    ACTIVATION = "activation"
    RETENTION = "retention"
    REFERRAL = "referral"
    REVENUE = "revenue"


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
    id: str
    name: StageName
    definition: str


class Transition(_VersionedNode):
    id: str
    name: str
    from_stage_id: str
    to_stage_id: str
    definition: str


class StakeholderArchetype(_VersionedNode):
    id: str
    name: str
    archetype_type: ArchetypeType
    # Backwards-compatible cache. The canonical trait graph is
    # StakeholderArchetype -[:HAS_TRAIT]-> Trait -[:HAS_LEVEL]-> TraitLevel.
    traits: dict[str, Any] = Field(default_factory=dict)
    role: Optional[str] = None
    segment: Optional[str] = None
    industry: Optional[str] = None
    company_size_band: Optional[str] = None
    definition: Optional[str] = None


class Offering(_VersionedNode):
    id: str
    name: str
    # company_name is a string prop kept for backwards compat. As of v1.1
    # the authoritative link is the OFFERED_BY edge to a Company node.
    # Will be deprecated in v2.
    company_name: str
    is_competitor: bool = False
    category: Optional[str] = None
    definition: Optional[str] = None


class Company(_VersionedNode, _TemporallyValid):
    """The organization that offers one or more Offerings. Added in v1.1 to
    give Offering→Company a proper edge for rollup queries.

    v1.4.0 additions:
      - industry, headquarters, ticker (schema.org-aligned identity props)
      - _TemporallyValid mixin (companies wind down, merge, rebrand)
    """
    id: str
    name: str
    domain: Optional[str] = None
    definition: Optional[str] = None
    industry: Optional[str] = None        # v1.4.0 — schema.org Organization.industry
    headquarters: Optional[str] = None    # v1.4.0 — city + country, free-form for v1
    ticker: Optional[str] = None          # v1.4.0 — stock ticker if public


class Person(_VersionedNode, _TemporallyValid):
    """A natural person who plays one or more StakeholderArchetype roles.

    Added in v1.4.0 to address the OntoClean role-as-sortal violation in
    StakeholderArchetype: the archetype is the ROLE (anti-rigid, dependent),
    not the entity that carries identity. Person is the +R+I sortal that
    plays the role.

    StakeholderArchetype is retained unchanged for backwards compatibility;
    new ingests that have clear individual identity should write a Person
    node + a PLAYS edge instead of a bare StakeholderArchetype.

    Triggering condition (per v2_spec.md): scale beyond a single-customer
    POC where the same individual plays role X at company A and role Y at
    company B. Until that scale, Person is opt-in.
    """
    id: str
    name: str
    role_title: Optional[str] = None      # e.g. "CFO", "Head of Procurement"
    company_id: Optional[str] = None      # backref to Company.id if known
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
    """A plausible level for an Attribute in a Market/period."""
    id: str
    attribute_id: str
    market_id: str
    value: Any  # coerced to str/float/bool by data_type on the Attribute
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
    """A plausible value for a Trait in a Market/period."""
    id: str
    trait_id: str
    market_id: str
    value: Any
    label: Optional[str] = None
    is_status_quo: bool = False


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


class EdgeConsumed(_Edge):
    """ExperimentRun -[:CONSUMED]-> any ontology context node."""
    label: Literal["CONSUMED"] = "CONSUMED"
    target_node_type: Optional[str] = None


class EdgeProduced(_Edge):
    """ExperimentRun -[:PRODUCED]-> Estimate."""
    label: Literal["PRODUCED"] = "PRODUCED"


# ---------------------------------------------------------------------------
# v1.4.0 — Continuant-to-Continuant primitives
#
# These six edges close the substrate-hygiene gap surfaced in
# sizzl-trustgraph#181: the LLM extractor was emitting competesWith /
# competitorOf / partnersWith / alternativeTo / acquired ~136 times across
# 423 chunks, all silently dropped because no matching object property was
# declared. Now they have proper homes.
#
# Plus one new edge (PLAYS) for the v1.4.0 Person → StakeholderArchetype
# role-binding pattern.
# ---------------------------------------------------------------------------


class EdgeCompetesWith(_Edge, _TemporallyValid):
    """Company -[:COMPETES_WITH]-> Company.

    Direct competitive relationship. Symmetric in practice but stored
    directionally — writers may emit both directions or rely on consumers
    to handle the symmetry. Confidence is required for downstream filtering.
    """
    label: Literal["COMPETES_WITH"] = "COMPETES_WITH"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class EdgePartneredWith(_Edge, _TemporallyValid):
    """Company -[:PARTNERED_WITH]-> Company.

    Strategic alliance, channel partnership, JV, or co-marketing. The
    partnership_type free-form prop captures the kind (e.g. "channel",
    "co-marketing", "JV", "supplier"). When in doubt, leave it null.
    """
    label: Literal["PARTNERED_WITH"] = "PARTNERED_WITH"
    partnership_type: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EdgeAcquired(_Edge):
    """Company -[:ACQUIRED]-> Company.

    M&A relationship. acquired_at is the close date when known. Not
    _TemporallyValid because acquisitions are point-in-time events whose
    effect persists — use acquired_at + the resulting Company structure
    rather than valid_from/valid_to.
    """
    label: Literal["ACQUIRED"] = "ACQUIRED"
    acquired_at: Optional[date] = None
    price: Optional[float] = None       # in USD if specified; null if undisclosed
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EdgeProducedBy(_Edge):
    """Offering -[:PRODUCED_BY]-> Company.

    Functionally redundant with the existing OFFERED_BY (Offering →
    Company), but accepted because LLM extractors emit this direction
    naturally ("X is produced by Y") and we lose data when we drop it as
    Unknown. Writers may choose either; downstream queries should treat
    OFFERED_BY and PRODUCED_BY as equivalent.
    """
    label: Literal["PRODUCED_BY"] = "PRODUCED_BY"


class EdgeAlternativeTo(_Edge):
    """Offering -[:ALTERNATIVE_TO]-> Offering.

    Functional substitute relationship. Foundational for choice-set
    construction — when buyers evaluate Offering A, they typically
    compare against its ALTERNATIVE_TO peers. similarity_score in [0,1]
    captures functional closeness when known.
    """
    label: Literal["ALTERNATIVE_TO"] = "ALTERNATIVE_TO"
    similarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EdgeComplementOf(_Edge):
    """Offering -[:COMPLEMENT_OF]-> Offering.

    Bundle / ecosystem complement — Offering B's value increases when
    A is also present (e.g. AppleCare complements iPhone). Distinct
    from ALTERNATIVE_TO which captures substitution.
    """
    label: Literal["COMPLEMENT_OF"] = "COMPLEMENT_OF"
    bundle_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EdgePlays(_Edge, _TemporallyValid):
    """Person -[:PLAYS]-> StakeholderArchetype.

    v1.4.0 role-binding: an individual plays an archetype role within
    a specific company context. role_context captures the company or
    deal scope when the same person plays different roles elsewhere.
    """
    label: Literal["PLAYS"] = "PLAYS"
    role_context: Optional[str] = None    # e.g. "at Acme Inc, 2024-2026"


# ---------------------------------------------------------------------------
# Convenience: registry for writers/importers
# ---------------------------------------------------------------------------

NODE_MODELS: dict[str, type[BaseModel]] = {
    "Market": Market,
    "Stage": Stage,
    "Transition": Transition,
    "StakeholderArchetype": StakeholderArchetype,
    "Person": Person,                     # v1.4.0
    "Offering": Offering,
    "Attribute": Attribute,
    "AttributeLevel": AttributeLevel,
    "Trait": Trait,
    "TraitLevel": TraitLevel,
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
    "OFFERED_BY": EdgeOfferedBy,
    "CONSUMED": EdgeConsumed,
    "PRODUCED": EdgeProduced,
    # v1.4.0 Continuant-Continuant edges
    "COMPETES_WITH": EdgeCompetesWith,
    "PARTNERED_WITH": EdgePartneredWith,
    "ACQUIRED": EdgeAcquired,
    "PRODUCED_BY": EdgeProducedBy,
    "ALTERNATIVE_TO": EdgeAlternativeTo,
    "COMPLEMENT_OF": EdgeComplementOf,
    "PLAYS": EdgePlays,
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
