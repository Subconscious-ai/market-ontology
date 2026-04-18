Full path 
  ~/subconscious-ai/
  ├── spice-harvester/        ← bash + python research pipeline
  │                             github.com/Subconscious-ai/spice-harvester
  │                             • ingest / query / lint / interview / interview-merge
  │                             • docs/INTEGRATION.md ← points at market-ontology
  │
  ├── market-ontology/        ← new, at ~/subconscious-ai/market-ontology/
  │                             github.com/Subconscious-ai/market-ontology
  │                             • @subconscious-ai/market-ontology (npm)
  │                             • market-ontology (PyPI when published)
  │                             • shared source of truth for the POC schema
  │
  └── ai-chatbot/             ← your existing Vercel repo; clone here when ready
                                 depends on @subconscious-ai/market-ontology
                                 reads spice-harvester's output/<slug>/wiki/
                                 writes interview answers back via subprocess

  Everything the ai-chatbot team can now build against

  1. Shared types — pnpm add @subconscious-ai/market-ontology once published, or local path dep before that.
  2. Trigger ingest — bash /path/to/spice-harvester/run.sh <email> from an API route.
  3. Tail progress — SSE off output/<slug>/wiki/log.md (pattern in docs/INTEGRATION.md).
  4. Read wiki — the 7 category pages + ontology.json for chat context.
  5. Write interview answers — bash /path/to/spice-harvester/run.sh <email> --interview '{...json...}' per executive turn, then --interview-merge every N answers to upgrade the
  ontology.
Market Simulation Ontology — v1 POC
Purpose
This package is the minimal ontology that sits between:

A wiki-style market research agent (+ executive interview input)
The Subconscious.ai discrete choice experiment engine
The ontology is context for the experiment, not the experiment itself. Subconscious owns experiment design and causal estimation. This repo owns the structured context that feeds Subconscious and the structured results that come back.

Scope
Single customer, single company, 12-month horizon.
POC-grade. See v2_spec.md for the parking lot of things deliberately cut.
Core model
Stakeholder archetypes + Offering attributes + Market context → Transition between AARRR stages → Part-worth estimates back from Subconscious.

Stack
Neo4j as the store. Bloom for customer-facing visualization.
Pydantic at the write boundary for schema enforcement.
Splink (separate job) for entity resolution on Offerings and StakeholderArchetypes.
APOC for JSONL import/export.
Postgres + pg_vector (optional, separate) if the research agent needs semantic retrieval over Evidence excerpts.
Graphiti is deliberately not in v1. Revisit in v2 if research-agent ingestion quality plateaus.
Node types (9)
Node	Purpose
Market	Scope boundary for every query
Stage	AARRR stage as a first-class node
Transition	The state change being modeled
StakeholderArchetype	Customer or competitor-side archetype
Offering	Object of study (product, service, SKU)
Attribute	Dimension of an Offering that can be varied
AttributeLevel	Plausible level for an Attribute in a Market/period
Evidence	Source grounding for any node
Estimate	Part-worth or other quantity returned from Subconscious
Edge types (10)
Transition -[:FROM]-> Stage
Transition -[:TO]-> Stage
Transition -[:IN_MARKET]-> Market
Transition -[:RELEVANT_TO]-> StakeholderArchetype
Transition -[:ABOUT]-> Offering

Offering -[:HAS_ATTRIBUTE]-> Attribute
Attribute -[:HAS_LEVEL]-> AttributeLevel
Attribute -[:RELEVANT_AT {score, valid_from, valid_to, evidence_ids}]-> Stage

Evidence -[:SUPPORTS]-> *
Estimate -[:ABOUT]-> *
Golden rules
No probabilities or part-worths on ontology nodes. Those are Estimates. Estimates point at ontology nodes; they don't mutate them.
Competitor combinations, treatments, and choice tasks live in Subconscious, not here. The ontology provides attributes, levels, archetypes, and context. Subconscious composes experiments.
If a value is conditional on model, period, or experiment, it is an Estimate.
Every node has schema_version. Every Estimate has ontology_snapshot_hash.
Temporal validity (valid_from, valid_to) applies to AttributeLevel, RELEVANT_AT edges, Estimate, and Evidence. Not to stable definitional nodes (Stage, Market scope, Transition definition).
Pipeline
Research agent + executive interview extract node and edge candidates with evidence into JSONL.
Pydantic validates at the write boundary.
APOC imports validated JSONL into Neo4j.
Splink runs entity resolution on Offerings and StakeholderArchetypes after each ingestion pass.
Customer reviews the graph in Bloom.
Experiment context is projected to JSON (see contracts/experiment_context.schema.json) and sent to Subconscious.
Subconscious returns results (see contracts/experiment_results.schema.json) which land as Estimate nodes.
What changed from v0
See MIGRATION.md.

What's cut and why
See v2_spec.md.

