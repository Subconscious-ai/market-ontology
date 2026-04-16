// v1 POC Neo4j constraints and indexes
// Run once per fresh database.

// Unique IDs
CREATE CONSTRAINT market_id IF NOT EXISTS FOR (n:Market) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT stage_id IF NOT EXISTS FOR (n:Stage) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT transition_id IF NOT EXISTS FOR (n:Transition) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT stakeholder_archetype_id IF NOT EXISTS FOR (n:StakeholderArchetype) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT offering_id IF NOT EXISTS FOR (n:Offering) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT attribute_id IF NOT EXISTS FOR (n:Attribute) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT attribute_level_id IF NOT EXISTS FOR (n:AttributeLevel) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (n:Evidence) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT estimate_id IF NOT EXISTS FOR (n:Estimate) REQUIRE n.id IS UNIQUE;

// Stage name uniqueness
CREATE CONSTRAINT stage_name IF NOT EXISTS FOR (n:Stage) REQUIRE n.name IS UNIQUE;

// Required property constraints (Neo4j 5+)
CREATE CONSTRAINT market_name_required IF NOT EXISTS FOR (n:Market) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT transition_name_required IF NOT EXISTS FOR (n:Transition) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT offering_name_required IF NOT EXISTS FOR (n:Offering) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT attribute_name_required IF NOT EXISTS FOR (n:Attribute) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT archetype_type_required IF NOT EXISTS FOR (n:StakeholderArchetype) REQUIRE n.archetype_type IS NOT NULL;
CREATE CONSTRAINT estimate_snapshot_required IF NOT EXISTS FOR (n:Estimate) REQUIRE n.ontology_snapshot_hash IS NOT NULL;

// Lookup indexes for Bloom and common queries
CREATE INDEX market_name IF NOT EXISTS FOR (n:Market) ON (n.name);
CREATE INDEX transition_name IF NOT EXISTS FOR (n:Transition) ON (n.name);
CREATE INDEX offering_name IF NOT EXISTS FOR (n:Offering) ON (n.name);
CREATE INDEX offering_company IF NOT EXISTS FOR (n:Offering) ON (n.company_name);
CREATE INDEX attribute_name IF NOT EXISTS FOR (n:Attribute) ON (n.name);
CREATE INDEX archetype_name IF NOT EXISTS FOR (n:StakeholderArchetype) ON (n.name);
CREATE INDEX archetype_type IF NOT EXISTS FOR (n:StakeholderArchetype) ON (n.archetype_type);
CREATE INDEX evidence_source IF NOT EXISTS FOR (n:Evidence) ON (n.source_type);
CREATE INDEX estimate_experiment IF NOT EXISTS FOR (n:Estimate) ON (n.subconscious_experiment_id);
CREATE INDEX estimate_type IF NOT EXISTS FOR (n:Estimate) ON (n.estimate_type);

// Temporal indexes
CREATE INDEX attribute_level_valid_from IF NOT EXISTS FOR (n:AttributeLevel) ON (n.valid_from);
CREATE INDEX estimate_valid_from IF NOT EXISTS FOR (n:Estimate) ON (n.valid_from);
