# Twenty Projection Contract

`twenty_projection.json` is the source manifest for projecting the ontology into Twenty. `twenty_app_contract.json` is generated from that manifest by `scripts/generate_twenty_app.py`; do not edit the generated contract by hand.

The projection keeps one shared ontology schema for every customer. It exposes `Company`, `Offering`, and `StakeholderArchetype` as the primary Twenty surfaces named `company`, `product`, and `persona`. Support objects stay linked rather than flattened away: products link to `Attribute` and `AttributeLevel`; personas link to `Trait` and `TraitLevel`; transitions, stages, evidence, estimates, experiment runs, and markets remain support records for provenance and experiment context.

Every projected object carries the same sync metadata:

- `ontology_node_id`
- `ontology_node_type`
- `ontology_schema_version`
- `projection_version`
- `source_run_id`
- `ontology_snapshot_hash`
- `synced_at`
- `source_updated_at`

Downstream sync ledgers should key rows by `tenant_id`, `ontology_node_type`, `ontology_node_id`, and `ontology_snapshot_hash`. That key maps a tenant-scoped ontology node snapshot to the corresponding Twenty record without relying on display names.

Relations are declared in the manifest and generated into the contract. Twenty object definitions must not maintain a separate hand-written relation graph. When `schema.py`, `twenty_projection.json`, or a generated contract changes, coordinate sibling PRs for any affected consumers in `causl.io`, `ai-chatbot`, and `spice-harvester`.
