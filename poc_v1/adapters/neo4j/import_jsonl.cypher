// APOC-based JSONL import for v1 POC seed data.
// Files should be placed in the Neo4j import/ directory.
// All writes here are post-Pydantic-validation; this just lands the data.

// --- Nodes ---

CALL apoc.load.json("file:///markets.jsonl") YIELD value
MERGE (n:Market {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///stages.jsonl") YIELD value
MERGE (n:Stage {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///transitions.jsonl") YIELD value
MERGE (n:Transition {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///stakeholder_archetypes.jsonl") YIELD value
MERGE (n:StakeholderArchetype {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///offerings.jsonl") YIELD value
MERGE (n:Offering {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///attributes.jsonl") YIELD value
MERGE (n:Attribute {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///attribute_levels.jsonl") YIELD value
MERGE (n:AttributeLevel {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///traits.jsonl") YIELD value
MERGE (n:Trait {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///trait_levels.jsonl") YIELD value
MERGE (n:TraitLevel {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///evidence.jsonl") YIELD value
MERGE (n:Evidence {id: value.id})
SET n += value.properties;

CALL apoc.load.json("file:///estimates.jsonl") YIELD value
MERGE (n:Estimate {id: value.id})
SET n += value.properties;

// --- Edges ---

CALL apoc.load.json("file:///edges_transition_from_stage.jsonl") YIELD value
MATCH (a:Transition {id: value.start_id})
MATCH (b:Stage {id: value.end_id})
MERGE (a)-[r:FROM]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_transition_to_stage.jsonl") YIELD value
MATCH (a:Transition {id: value.start_id})
MATCH (b:Stage {id: value.end_id})
MERGE (a)-[r:TO]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_transition_in_market.jsonl") YIELD value
MATCH (a:Transition {id: value.start_id})
MATCH (b:Market {id: value.end_id})
MERGE (a)-[r:IN_MARKET]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_transition_relevant_to.jsonl") YIELD value
MATCH (a:Transition {id: value.start_id})
MATCH (b:StakeholderArchetype {id: value.end_id})
MERGE (a)-[r:RELEVANT_TO]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_transition_about_offering.jsonl") YIELD value
MATCH (a:Transition {id: value.start_id})
MATCH (b:Offering {id: value.end_id})
MERGE (a)-[r:ABOUT]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_offering_has_attribute.jsonl") YIELD value
MATCH (a:Offering {id: value.start_id})
MATCH (b:Attribute {id: value.end_id})
MERGE (a)-[r:HAS_ATTRIBUTE]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_attribute_has_level.jsonl") YIELD value
MATCH (a:Attribute {id: value.start_id})
MATCH (b:AttributeLevel {id: value.end_id})
MERGE (a)-[r:HAS_LEVEL]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_persona_has_trait.jsonl") YIELD value
MATCH (a:StakeholderArchetype {id: value.start_id})
MATCH (b:Trait {id: value.end_id})
MERGE (a)-[r:HAS_TRAIT]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_trait_has_level.jsonl") YIELD value
MATCH (a:Trait {id: value.start_id})
MATCH (b:TraitLevel {id: value.end_id})
MERGE (a)-[r:HAS_LEVEL]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_attribute_relevant_at.jsonl") YIELD value
MATCH (a:Attribute {id: value.start_id})
MATCH (b:Stage {id: value.end_id})
MERGE (a)-[r:RELEVANT_AT]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_evidence_supports.jsonl") YIELD value
MATCH (a:Evidence {id: value.start_id})
MATCH (b {id: value.end_id})
MERGE (a)-[r:SUPPORTS]->(b)
SET r += value.properties;

CALL apoc.load.json("file:///edges_estimate_about.jsonl") YIELD value
MATCH (a:Estimate {id: value.start_id})
MATCH (b {id: value.end_id})
MERGE (a)-[r:ABOUT]->(b)
SET r += value.properties;
