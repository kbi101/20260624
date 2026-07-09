"""Neo4j storage layer — persist extracted entities and relations graph."""

from hist.neo4j_driver.connect import run_cypher, HistDriver


def store_entity(entity_dict, source_url):
    """Upsert a single entity into Neo4j. Returns True if node was created/updated."""
    eid = entity_dict.get("node_id")
    etype = entity_dict.get("entity_type", "event").capitalize()  # "Event" | "Person"
    label = etype

    props = {k: v for k, v in entity_dict.items() if k not in ("node_id", "entity_type")}

    cyph = f"""
    MERGE (n:{label} {{node_id: $nid}})
    SET n += $props, n._source_url = $url, n._ingested_at = toString(timestamp())
    RETURN n
    """

    session = HistDriver.get_session()
    rec = session.run(cyph, nid=eid, props=props, url=source_url).single()
    session.close()
    return rec is not None


def store_relation(source_id, target_id, rel_type, attrs=None):
    """Create a typed edge between two existing entities by their IDs."""
    safe_type = rel_type.upper().replace(" ", "_").replace("-", "_")

    cyph = f"MATCH (a {{{'node_id: $sid'}}}), (b {{node_id: $tid}}) MERGE (a)-[:{safe_type}]->(b)"

    session = HistDriver.get_session()
    exists = bool(session.run(cyph, sid=source_id, tid=target_id).single())
    session.close()
    return exists


def batch_ingest(entities, relations):
    """Write all extracted data one transaction safe pass."""
    created, updated = 0, 0

    for ent in entities:
        ok = store_entity(ent, ent.get("source_url", ""))
        if ok: created += 1
        else: updated += 1

    for rel_tuple in relations:
        src = rel_tuple["source_id"]
        tgt = rel_tuple["target_id"]
        r_type = rel_tuple["relation_type"]
        store_relation(src, tgt, r_type)

    return {"created_nodes": created, "updated_existing": updated, "edges_written": len(relations)}


def find_entity(node_id):
    """Lookup an entity record from its unique ID."""
    row = run_cypher("MATCH (n) WHERE n.node_id = $nid RETURN n", {"nid": node_id})
    return row[0].get("n") if row else None


def count_by_type():
    """Snapshot how many Event vs Person nodes exist right now."""
    evts = run_cypher("MATCH (n:Event) RETURN count(n) AS events")
    peeps = run_cypher("MATCH (n:Person) RETURN count(n) AS persons")
    return {"events": evts[0].get("events", 0), "persons": peeps[0].get("persons", 0)} if evts and peeps else {"events": 0, "persons": 0}


def delete_entity(node_id):
    """Remove an entity by node_id."""
    run_cypher("MATCH (n) WHERE n.node_id = $nid DELETE n", {"nid": node_id})
