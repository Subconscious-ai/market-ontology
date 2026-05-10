# Accepted-State Spine Pointer

market-ontology owns schema/contracts, projection validation, change classes,
lighthouse fixtures, and source-of-truth drift checks for the accepted-state
spine.

Canonical ADR: `docs/adr/0001-accepted-state-spine.md`.

Operating loop:

```text
Inputs -> Evidence Inbox -> Claim Adjudicator -> Twenty Accepted Records -> Projection Pack
```

Accepted state lives in Twenty. This repo does not own operational records; it
owns the contract that accepted records and generated projections must satisfy.
