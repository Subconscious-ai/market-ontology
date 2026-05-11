# ADR 0003: Twenty Deferral — TrustGraph as Accepted-State Store for the POC

Date: 2026-05-10

Status: accepted

Supersedes the "Twenty as canonical accepted state" position in
[ADR 0001](0001-accepted-state-spine.md) and [ADR 0002](0002-operating-ontology-spine.md).

Mirrors the cross-repo decision recorded in
[`Subconscious-ai/sizzl-trustgraph#6`](https://github.com/Subconscious-ai/sizzl-trustgraph/issues/6).

## Context

ADRs 0001 and 0002 established Twenty as the canonical accepted-state
record store for operational ontology data. That was the right call when
the only credible alternative was a hand-rolled Postgres-as-truth
substrate. It is no longer the right call now that TrustGraph is the
intended downstream backend (per `sizzl-trustgraph#5/#10/#12`).

The simplest POC is TrustGraph-only for backend knowledge: Library,
ontology extraction, collections, graph/object storage, GraphRAG,
Workbench, and provenance. Twenty would only add value if we needed
customer-facing structured editing and permissions beyond what
TrustGraph + Sizzl UI provide. We do not need that for the first loop.

## Decision

**Twenty is deferred from the primary POC path.**

The primary POC accepted-state path is:

```text
spice (discovery + audit gate)
  -> source registry (sizzl-trustgraph#10)
  -> changedetection.io watch (per #12 audit signal)
  -> TrustGraph Library
  -> market-ontology-config flow (extraction)
  -> TrustGraph graph + object + provenance layer
  -> Sizzl UI / executive interview / downstream agents
```

TrustGraph is the canonical accepted-state store. spice-harvester
produces audited, target-matched, source-corroborated records and
hands them to TrustGraph via Agent B's `services/ingestion/spice/`
adapter (per `sizzl-trustgraph#5`).

Twenty may later be **populated from TrustGraph** as an optional CRM /
editing projection if customer-facing record workflows justify it.
That is a future ADR, not a current dependency.

## Store Boundaries (revised)

| Layer | Role | Owner |
|---|---|---|
| spice-harvester | Source discovery + audit gate. Produces `source_registry.jsonl` (per `sizzl-trustgraph#10`) and `audit_record.jsonl` (per `sizzl-trustgraph#12`). Never writes accepted state. | spice-harvester |
| TrustGraph Library + graph + object + provenance | **Canonical accepted state.** Everything that the executive interview, Sizzl UI, or downstream agents read as fact lives here. | TrustGraph (vendored) |
| market-ontology | Schema contract + projection shape. Not a runtime database. | market-ontology |
| ai-chatbot / Sizzl UI | Reads accepted state from TrustGraph. Writes corrections back through audited paths. | ai-chatbot |
| Twenty | **Deferred.** Not a current dependency. May later be populated *from* TrustGraph as an optional CRM/editing surface. | n/a (deferred) |
| Graphiti / Falkor | Retrieval projection only. Never accepted state. | burn-substrate |
| Zep | Per-exec memory only. Never accepted state. | (per-exec) |

## What changes from 0001 / 0002

- **Lines that say "Twenty accepted records are canonical":** read as
  "TrustGraph accepted records are canonical" until 0001 and 0002 are
  rewritten or retired.
- **Lines that say "Spice does not write accepted records":** unchanged
  — spice still doesn't write accepted records. Only the destination
  changes (TrustGraph instead of Twenty).
- **Spice → Twenty → raw-file-export → TrustGraph:** removed. Direct
  Spice → TrustGraph adapter is the path.
- **Twenty in the deprecation matrix:** added as `Deferred`. Not
  removed; not active either.

## Forbidden drift (additive to 0001/0002)

- Do not call Twenty an ingestion prerequisite.
- Do not implement a Twenty adapter on the spice side without a
  superseding ADR.
- Do not claim TrustGraph is a full CRM. (It is not. CRM-style editing
  is what Twenty would add later if needed.)

## Reintroduction rule

If Twenty is reintroduced, it is reintroduced as a **projection from
TrustGraph**, not as an ingestion source of record. Any ADR that
revises this decision must:

1. Identify the customer-facing edit/permissions workflow that
   TrustGraph + Sizzl UI cannot serve.
2. Specify the TrustGraph → Twenty projection adapter contract.
3. Pin tests that prevent Twenty from becoming an ingestion
   prerequisite (the failure mode this ADR exists to prevent).

## Cross-repo links

- `Subconscious-ai/sizzl-trustgraph#6` (decision)
- `Subconscious-ai/sizzl-trustgraph#5` (Spice → TrustGraph adapter)
- `Subconscious-ai/sizzl-trustgraph#10` (source registry shape)
- `Subconscious-ai/sizzl-trustgraph#12` (audit gate)
- `Subconscious-ai/spice-harvester#258` (umbrella) +
  `Subconscious-ai/spice-harvester#260` (C-2 PR — paired with this
  ADR)
- `Subconscious-ai/spice-harvester#257` (the plan that scoped this work)

## Gates

No later implementation should proceed until agents can answer:

- Where does accepted truth live? **TrustGraph.**
- Where does Twenty fit? **Nowhere in the first POC loop. Possibly a
  later projection from TrustGraph.**
- Which sizzl-trustgraph issue defines the Spice → TrustGraph contract?
  **#5, #10, #12.**
- Which spice-harvester PR produces the source registry that Agent B's
  adapter lifts? **#260.**
