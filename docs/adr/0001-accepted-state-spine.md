# ADR 0001: Accepted-State Spine

Status: Accepted
Date: 2026-05-09

## Decision

Subconscious market intelligence uses this operating loop:

```text
Inputs -> Evidence Inbox -> Claim Adjudicator -> Twenty Accepted Records -> Projection Pack
```

accepted state lives in Twenty. collectors produce candidates. The Claim
Adjudicator turns source-backed candidates into accepted, rejected, conflicted,
or review-needed claims. The Projection Pack generates every downstream view
from accepted Twenty records.

## Store Boundaries

- Twenty Accepted Records are the source of record for accepted operational
  ontology state.
- market-ontology owns schema, contracts, projection validation, change
  classes, and fixture shape.
- spice-harvester owns collection, source events, evidence candidates, claim
  candidates, and adjudication inputs. It does not write accepted records.
- ai-chatbot owns chat, Sizzle, review UI, accepted-state actions, and
  projection display. Accepted writes go through approved server-side paths.
- wiki and dossier are projections, not canonical stores.
- kg_seed is superseded by ontology_snapshot as a generated projection
  artifact. Existing kg_seed paths are compatibility surfaces until migrated.
- Graphiti/Falkor is a retrieval projection. It never creates accepted state.
- Zep is per-exec memory. It is not an ontology or accepted-state store.
- Rowboat and PageIndex are not core-path dependencies. Rowboat may become an
  optional input lane; PageIndex may become a long-document source index.
- Spice accepted writes are blocked. Spice produces candidates only; it never
  writes Twenty Accepted Records directly.

## Change Classes

| Class | Name | Rule |
| --- | --- | --- |
| Class 0 | local implementation | Stays inside one repo and does not touch contracts or accepted state. |
| Class 1 | local contract-adjacent | Touches one repo's adapter, projection, or validation around an existing contract. |
| Class 2 | cross-repo contract | Changes shared schema, generated contracts, or wire shape. Requires coordinated PRs. |
| Class 3 | source-of-record / accepted-state | Changes Twenty accepted records or accepted-write policy. Requires human approval. |
| Class 4 | breaking change | Removes or changes existing contract semantics. Requires ADR and migration plan. |

## Forbidden Drift

- Do not call wiki, dossier, Sizzle DAG, Graphiti, Falkor, Zep, Rowboat,
  PageIndex, raw chunks, source events, evidence candidates, or claim
  candidates canonical accepted state.
- Do not load raw chunks into Twenty as accepted Evidence.
- Do not include candidate claims in experiment context by default.
- Do not let Graphiti, Falkor, or Zep write accepted records.
- Do not introduce a parallel ontology in ai-chatbot, spice-harvester, or a
  retrieval store.

## Accepted Write Boundary

Accepted writes are allowed only through approved server-side ai-chatbot paths
that enforce tenancy, authorization, schema validation, audit metadata, and
projection refresh. Ambiguous chat corrections become Evidence Inbox source
events and ClaimCandidate records before adjudication. Explicit authorized
corrections write a correction source event, update Twenty, and regenerate the
Projection Pack.

## Projection Pack

The Projection Pack is generated from accepted Twenty records plus the
market-ontology contract. It includes ontology_snapshot, Sizzle DAG data,
generated wiki/dossier, experiment_context.json, and optional Graphiti/Falkor
retrieval projection. Projection failure must never mutate Twenty.

## Deprecation Matrix

| Surface | New role |
| --- | --- |
| wiki/dossier | Projection only; generated from accepted records where possible |
| kg_seed | Compatibility name for generated ontology_snapshot |
| wiki/claims.jsonl | Compatibility adapter only; log usage |
| Spice accepted writes | Blocked; Spice produces candidates only |
| raw chunks | Extraction material only; not accepted Evidence |
| Sizzle DAG | Accepted structure view only; not canonical |
| Graphiti/Falkor | Retrieval projection only; never accepted state |
| Zep | Per-exec memory only; not ontology truth |
| Rowboat | Parked optional input lane; not core path |
| PageIndex | Parked long-document source index; not core path |
| LinkML | Deferred migration candidate; do not redesign schema |

Compatibility readers for `kg_seed` or `wiki/claims.jsonl` must warn or log
usage, then migrate consumers to Evidence Inbox, ClaimCandidate,
AdjudicatedClaim, Twenty Accepted Records, or Projection Pack surfaces.

## Cleanup Loop

The new spine does not delete old lanes by itself. Cleanup is a governed loop:

```text
Inventory old lanes and data paths
-> Classify
-> Active / Compatibility only / Archived / Delete candidate
-> Add warnings and drift checks
-> Confirm no consumers
-> Archive or remove
```

Delete obsolete code paths aggressively. Archive provenance carefully. Never delete lineage needed to explain a past decision or experiment.
One accepted state. Many inputs. Many projections. No ghost canons.

Accepted Twenty records should usually be archived or tombstoned before hard
delete:

```text
status = archived
valid_to = timestamp
archived_reason = ...
superseded_by = ...
```

Hard deletion is allowed only for never-accepted records, test/demo data, or
records covered by an explicit retention policy with no snapshot, experiment,
or evidence lineage dependency.

Raw collector data may be removed only after durable provenance is preserved:

```text
source_ref
source URL or path
content hash
excerpt used as evidence
retrieval lane/query
timestamp
```

The first cleanup pass is audit-only. It inventories, classifies, warns, and
checks consumers; it does not hard-delete repo or runtime data.

## Gates

No later implementation should proceed until agents can answer:

- Where does accepted truth live?
- Which repo owns schema/contracts?
- Which systems are projections or memories only?
- Which change class applies?
- Which tests prove source-of-truth drift is blocked?
