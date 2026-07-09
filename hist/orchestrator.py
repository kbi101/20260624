"""Hist Orchestrator — wires scraper → extractor → normalizer → storage end-to-end."""

from hist.scraper.wikipedia import fetch_full_page
from hist.extraction.extractor import extract_facts, extract_relations
from hist.normalization.normalizer import normalize_node_id
from hist.storage.store_nodes_edges import batch_ingest, count_by_type
from hist.url_queue.queue import get_next_url, mark_completed
from hist.neo4j_driver.connect import HistDriver, run_cypher, run_cypher_single


def bootstrap_schema():
    """Create DB if it doesn't exist and ensure unique constraints on Event/Person node_id."""
    try:
        HistDriver.get_driver().execute_query("CREATE DATABASE hist IF NOT EXISTS")
    except Exception:
        pass
    session = HistDriver.get_session()
    session.run(
        "CREATE CONSTRAINT event_node_id_unique IF NOT EXISTS FOR (n:Event) REQUIRE n.node_id IS UNIQUE"
    )
    session.run(
        "CREATE CONSTRAINT person_node_id_unique IF NOT EXISTS FOR (n:Person) REQUIRE n.node_id IS UNIQUE"
    )
    session.close()


def ingest_page(url):
    """Ingest a single Wikipedia page through the full pipeline. Returns stats dict."""
    page_text = fetch_full_page(url)
    if not page_text:
        mark_completed(url)
        return {"step": "fetch", "status": "failed", "url": url}

    raw_entities = extract_facts(page_text)
    if not raw_entities:
        mark_completed(url)
        return {"step": "extract_entities", "status": "empty", "url": url}

    entities = []
    for ent in raw_entities:
        cand_id = ent.get("node_id", "")
        name = ent.get("name", cand_id)
        canon_id, _ = normalize_node_id(cand_id, name)
        ent["node_id"] = canon_id
        ent.setdefault("source_url", url)
        entities.append(ent)

    raw_relations = extract_relations(entities, page_text)

    stats = batch_ingest(entities, raw_relations)
    mark_completed(url)
    stats["url"] = url
    return stats


def ingest_queue(run_all=False):
    """Process the URL queue. If run_all=False, process one page and return."""
    bootstrap_schema()

    if not run_all:
        url = get_next_url()

        if not url:
            return {"status": "queue_empty"}
        return ingest_page(url)

    results = []
    while True:
        url = get_next_url()
        if not url:
            break
        results.append(ingest_page(url))
    return results


def graph_stats():
    """Return current node/edge counts from Neo4j."""
    nodes = count_by_type()
    edge_rec = run_cypher_single("MATCH ()-[e]->() RETURN count(e) AS edges")
    nodes["edges"] = edge_rec.get("edges", 0) if edge_rec else 0
    return nodes
