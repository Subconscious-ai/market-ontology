// Bloom search phrases for customer-facing exploration.
// Load these in Bloom as saved searches.

// --- Transition exploration ---

// Show transitions in a market
MATCH (t:Transition)-[:IN_MARKET]->(m:Market {name: $market_name})
MATCH (t)-[:FROM]->(sf:Stage)
MATCH (t)-[:TO]->(st:Stage)
RETURN t, m, sf, st;

// Show archetypes participating in a transition
MATCH (t:Transition {name: $transition_name})-[:RELEVANT_TO]->(s:StakeholderArchetype)
RETURN t, s;

// --- Attribute / Level exploration ---

// Show attributes relevant at a stage, with scores and evidence
MATCH (a:Attribute)-[r:RELEVANT_AT]->(s:Stage {name: $stage_name})
WHERE (r.valid_from IS NULL OR r.valid_from <= date($as_of))
  AND (r.valid_to IS NULL OR r.valid_to >= date($as_of))
RETURN a, r, s
ORDER BY r.score DESC;

// Show levels for an attribute in a market at a point in time
MATCH (a:Attribute {name: $attribute_name})-[:HAS_LEVEL]->(l:AttributeLevel)
WHERE l.market_id = $market_id
  AND (l.valid_from IS NULL OR l.valid_from <= date($as_of))
  AND (l.valid_to IS NULL OR l.valid_to >= date($as_of))
RETURN a, l;

// Show offering attribute landscape
MATCH (o:Offering {name: $offering_name})-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_LEVEL]->(l:AttributeLevel)
RETURN o, a, l;

// --- Estimates (experiment results) ---

// Show all estimates for a transition
MATCH (e:Estimate)-[:ABOUT]->(t:Transition {name: $transition_name})
RETURN e, t
ORDER BY e.estimated_at DESC;

// Show part-worths for an attribute level across archetypes
MATCH (e:Estimate {estimate_type: 'part_worth'})-[:ABOUT]->(l:AttributeLevel {id: $level_id})
RETURN e, l
ORDER BY e.value DESC;

// Show all estimates from a Subconscious experiment
MATCH (e:Estimate {subconscious_experiment_id: $experiment_id})
OPTIONAL MATCH (e)-[:ABOUT]->(target)
RETURN e, target;

// --- Evidence provenance ---

// Show evidence supporting an attribute level
MATCH (ev:Evidence)-[:SUPPORTS]->(l:AttributeLevel {id: $level_id})
RETURN ev, l;

// Show everything an evidence record supports
MATCH (ev:Evidence {id: $evidence_id})-[:SUPPORTS]->(n)
RETURN ev, n;

// Full provenance for an offering: attributes, levels, and supporting evidence
MATCH (o:Offering {name: $offering_name})-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_LEVEL]->(l:AttributeLevel)
OPTIONAL MATCH (ev:Evidence)-[:SUPPORTS]->(l)
RETURN o, a, l, ev;
