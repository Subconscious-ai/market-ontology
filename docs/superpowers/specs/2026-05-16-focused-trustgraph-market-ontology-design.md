# Focused TrustGraph-Compatible Market Ontology — Design

**Date:** 2026-05-16
**Status:** Design — pending implementation plan
**Repos touched:** `market-ontology` (primary), `spice-harvester` (`lib/ontology_extraction`, secondary)

## Context & goal

The decision is to *incorporate TrustGraph because it forces discipline about a
true knowledge graph*. The Pareto reframe of that decision: **the discipline
lives in the contract, not the container.** A focused OWL ontology with real
domain/range axioms, CI-enforced, and an extractor validated against it — that
*is* the forcing function. TrustGraph's 22-container runtime is not required to
get it.

So Phase 1 builds exactly the high-leverage 10%: a focused, TrustGraph-
compatible OWL market ontology, enforced in CI, with the existing extractor
pointed at it. It deliberately cuts the 90% — standing up and qualifying a TG
runtime — for ~10% loss (no `graph-rag`, no TG flow orchestration), a loss that
is moot because the decision was made on discipline grounds, not latency
(consistent with `ai-chatbot` ADR 0009's "choose the lean path consciously"
branch).

## Non-goals (explicitly cut)

- Standing up a TrustGraph runtime instance — the qualified config, the
  resourced host, RabbitMQ/Cassandra/Qdrant, the convergence latency gate.
- `graph-rag`, the chat-runtime integration, Memgraph/FalkorDB evaluation.
- These are deferred to a future phase, gated by a *demonstrated* need
  (Spice corpus volume in the thousands of documents, or a proven multi-hop
  retrieval requirement). YAGNI until then.

## Architecture

A focused ~6-class OWL ontology, produced by a **projection layer** in
`market-ontology/poc_v1/ontology/` — un-retiring the layer commit `9ab0ad1`
(#65) deleted, modernised for schema **v1.5.0**. The projection is aligned to
**schema.org / GoodRelations / PROV-O** (see "Ontology reuse" below). CI
enforces schema↔projection drift and OWL validity. The existing
`lib/ontology_extraction` extractor in `spice-harvester` is pointed at the
generated OWL artifact.

```
schema.py (v1.5.0, canonical, full ~15 classes)
  + trustgraph_projection.json  (the focused ~6-class subset config)
        │
        ▼  generate_trustgraph_ontology.py
  trustgraph_ontology.json  (real OWL: owl:Class, rdfs:domain/range, owl:Restriction)
        │
        ▼  consumed by
  spice-harvester lib/ontology_extraction  →  typed, domain/range-validated,
                                              PROV-O-provenanced triples
```

The full v1.5.0 ontology stays canonical in `schema.py`. The TG projection is a
deliberate, documented *subset* — TrustGraph best practice: "a 5-class ontology
with 10 well-defined properties extracts more reliably than a 50-class
hierarchy."

## The focused 6-class ontology

Grounded in a research pass over existing ontologies. Three classes reuse
established standards; three have no usable standard and are built minimal.

| # | Class | Strategy | URI / basis |
|---|---|---|---|
| 1 | **Product** | Reuse | `mkt:Product ⊑ schema:Product`. Attributes & levels via `schema:additionalProperty` → `schema:PropertyValue`. Pricing via `schema:Offer` / `schema:PriceSpecification`. |
| 2 | **Organization/Brand** | Reuse | `schema:Organization` + `schema:Brand` — the market actor behind a product. |
| 3 | **Persona** | Align | `mkt:Persona ⊑ schema:Audience`. Traits via the same `schema:additionalProperty` → `schema:PropertyValue` pattern. Customer *segment* collapses into Persona/Audience — not a separate class. |
| 4 | **JourneyStage** | Build | `mkt:JourneyStage`, `owl:oneOf` five named individuals (Acquisition, Activation, Retention, Revenue, Referral). `mkt:StageTransition` with `mkt:fromStage`/`mkt:toStage`/`mkt:triggeringAction` (range `schema:Action`). A customer *decision* collapses into a StageTransition — not a separate class. |
| 5 | **Job** | Build | `mkt:Job` (Job-To-Be-Done), standalone. JTBD's five-element vocabulary used as *property names*, not classes. |
| 6 | **Pain** | Build | `mkt:Pain` (unmet need / customer pain), linked `mkt:obstructsJob` → `mkt:Job`, `mkt:painAddressedBy` → `mkt:Product`. |
| — | **Evidence** | Reuse | **PROV-O** (`prov:wasDerivedFrom` etc.) — a cross-cutting provenance layer on every extracted fact, not a domain class. |

**Original predicates** (each an `owl:ObjectProperty` with explicit
`rdfs:domain`/`rdfs:range` — this domain/range is what constrains the
extractor): `mkt:competesWith` (symmetric, Product↔Product), `mkt:fromStage`,
`mkt:toStage`, `mkt:triggeringAction`, `mkt:obstructsJob`,
`mkt:painAddressedBy`, `mkt:hasPersona` (Product→Persona), `mkt:pursuesJob`
(Persona→Job).

### Ontology reuse — key judgments from the research

1. **schema.org alignment is the right pragmatic backbone** — LLMs are
   saturated with schema.org from training data, so `schema:Product` /
   `schema:Audience` in the extraction prompt yield reliable extraction.
2. **schema.org is NOT OWL DL** — its `domainIncludes`/`rangeIncludes` are
   non-constraining suggestions. The projection **must restate domain/range as
   real `rdfs:domain`/`rdfs:range` / `owl:Restriction`**, even on reused
   schema.org classes. That restatement is precisely what makes the extractor
   validate triples. GoodRelations (real OWL Lite) is the pattern source.
3. **The `additionalProperty` → `PropertyValue` pattern is the biggest reuse
   win** — one GoodRelations-derived construct handles both product
   attributes-and-levels and persona traits. Use it in both.
4. **User Journey (AARRR) and JTBD/Pains have no reusable standard** —
   confirmed, not assumed. AARRR and JTBD are *frameworks*, not vocabularies;
   the one academic OWL artifact (BPES) is brand-new and unadopted. Build these
   three classes; keep them minimal; do not adopt CJML or BPES as namespaces.
5. **Resist class inflation** — hold at ~6. Decision → StageTransition;
   Segment → Persona; JTBD's five elements → properties of one `Job` class.

## Workstreams

**W1 — Compatibility audit.** Assess `market-ontology` v1.5.0 (~15 classes)
against the 6-class target and the research. Produce a written audit:
class-by-class keep/cut/merge decision, the property set, the gaps. Lock the
focused subset. *Pure analysis; no code.*

**W2 — The ontology + projection layer.** In `market-ontology/poc_v1/ontology/`,
un-retire and modernise the layer #65 removed: `trustgraph_projection.json` (the
subset config), `generate_trustgraph_ontology.py` (the generator), and the
drift tests. The generated `trustgraph_ontology.json` must be **real OWL**.
Wire schema↔projection drift detection and OWL validation into CI
(`validate-fast.sh`). *Pure, offline, zero infrastructure.*

**W3 — Point the extractor at it.** In `spice-harvester` `lib/ontology_extraction`,
consume the new OWL artifact. Verify domain/range validation works against it:
the existing competitor fixtures extract with zero domain/range rejections on
valid input.

## Risks & error handling

- **schema.org not constraining** → mitigated by restating real OWL axioms (W2).
- **Journey / JTBD extraction yield is unproven.** AARRR transitions, Jobs and
  Pains are process/strategic knowledge that market source documents rarely
  state in extractable form. The three built classes are *scaffolded* — defined
  correctly — but their population from real extraction is a known risk. Phase 1
  success is measured on the **Product / Persona / competitor core** (high
  reuse, high extraction yield); Journey/Job/Pain population is a stretch goal
  and a Phase-2 measurement, not a Phase-1 gate.
- **Class inflation** — W1 must hold the line at ~6; the audit is the gate.

## Testing & success criteria

- **Drift tests** — schema `NODE_MODELS` ↔ projection `classes`, failing loud
  on drift (the #60 `_assert_class_coverage` pattern, restored).
- **OWL validation** — the generated artifact is valid OWL (`owl:Class`,
  `rdfs:subClassOf`, `owl:ObjectProperty`, `rdfs:domain`/`rdfs:range`,
  `owl:Restriction`), checked by an OWL validator in CI.
- **Extraction check** — `lib/ontology_extraction` run against the new OWL
  produces domain/range-valid triples for the Product/Persona/competitor core
  on the existing fixtures, with **zero domain/range rejections on valid
  input**.
- Phase 1 is **done** when: the focused OWL artifact generates and passes CI,
  and the extractor validates against it on the competitor fixtures.

## Out of scope / future phases

TrustGraph runtime, `graph-rag`, the ai-chatbot chat integration, Memgraph/
FalkorDB, and Journey/JTBD population at scale — all deferred, each gated by a
demonstrated need.
