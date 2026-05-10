# Accepted-State Cross-Repo Smoke Skeleton

This is the minimal smoke path for the accepted-state spine:

```text
Inputs -> Evidence Inbox -> Claim Adjudicator -> Twenty Accepted Records -> Projection Pack
```

accepted state lives in Twenty. The smoke proves each repo keeps that boundary
visible before later implementation work proceeds.

## market-ontology

Owns schema, contracts, projection validation, source-of-truth drift checks,
the lighthouse fixture skeleton, and this smoke skeleton.

Command:

```bash
python3 tests/test_accepted_state_spine_contract.py -v
```

## spice-harvester

Owns collection, source events, evidence candidates, claim candidates, and
adjudication inputs. The smoke confirms Spice does not write accepted records.

Command:

```bash
python3 -m pytest tests/test_accepted_state_spine_doc.py -q
```

## ai-chatbot

Owns chat, Sizzle, review UI, accepted-state actions, projection display, and
the approved server-side accepted-write boundary. The smoke confirms Graphiti,
Falkor, and Zep cannot be accepted-record writers.

Command:

```bash
pnpm exec tsx --test tests/unit/accepted-state-spine-doc.test.ts
```

## Gate

The three repo smokes must answer:

- Where does accepted truth live?
- Which source-of-truth drift checks are active?
- Where is the accepted-write boundary?
- Which Projection Pack outputs are generated from accepted records?
