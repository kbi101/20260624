#!/usr/bin/env python3
"""Batch ingest all pending Wikipedia URLs from HIST queue."""

import sys
from hist.url_queue.queue import _load, mark_completed
from hist.scraper.wikipedia import fetch_full_page
from hist.extraction.extractor import extract_with_cache
from hist.storage.store_nodes_edges import batch_ingest, is_url_ingested


def main():
    q = _load()
    urls = q.get("pending", [])
    if not urls:
        print("No pending URLs in queue.")
        return

    print(f"Processing {len(urls)} pending pages...\n")

    skipped_stores = 0

    for i, url in enumerate(urls):
        topic = url.rsplit("/")[-1].replace("_", " ")
        try:
            print(f"[{i+1}/{len(urls)}] Fetching: {topic}... ", end="", flush=True)
            text = fetch_full_page(url)
            print(f"OK ({len(text)} chars)", flush=True)

            print(f"  Extracting entities & relations... ", end="", flush=True)
            sys.stdout.flush()
            ent, rels, from_cache = extract_with_cache(url, text)
            cache_tag = "[CACHED]" if from_cache else ""
            persons = sum(1 for e in ent if e.get("entity_type") == "person")
            events = sum(1 for e in ent if e.get("entity_type") == "event")
            print(f"OK ({len(ent)} entities, {len(rels)} relations) {cache_tag}", flush=True)

            # Add source_url to each entity
            for e in ent:
                e["source_url"] = url

            if is_url_ingested(url):
                print(f"  [SKIP] All nodes already in Neo4j — skipping storage", flush=True)
                skipped_stores += 1
            else:
                result = batch_ingest(ent, rels)
                print(f"  Stored: {result}", flush=True)

            mark_completed(url)

        except Exception as exc:
            print(f"FAILED: {exc}", flush=True)

    # Summary
    from hist.neo4j_driver.connect import run_cypher
    nodes = [r for r in run_cypher("MATCH (n) RETURN count(n) AS c")]
    edges = [r for r in run_cypher("MATCH ()-->() RETURN count(*) AS c")]
    print(f"\n=== Final DB state ===")
    print(f"  Total nodes: {dict(nodes[0])['c']}")
    print(f"  Total edges: {dict(edges[0])['c']}")

    lincoln_eds = [r for r in run_cypher(
        "MATCH (a)-[r]->(b) WHERE a.node_id='abraham_lincoln' OR b.node_id='abraham_lincoln' RETURN type(r) AS rel, a.node_id AS src, b.node_id AS tgt"
    )]
    print(f"  Lincoln direct edges: {len(lincoln_eds)}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
