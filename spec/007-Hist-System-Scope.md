# Phase 7 — HIST System Scope (v0.2)

## Overview

HIST is a Neo4j-backed knowledge graph of **historical events and people**. Truth comes exclusively from Wikipedia-derived sources — scraped via Morphos `web_fetch` (Playwright Chrome), LLM-extracted, and stored into the graph. LLM has two roles only: *(1)* extract entities and relationships from source text; *(2)* transform retrieved facts into answers after Cypher traversal. Graph traversal answers all factual queries deterministically grounded in Wiki-derived truth.

## Design Principles

1. **Local-only** — all components run on user's machine (Neo4j at `bolt://localhost:7689`).
2. **Modular** — each component (scraper, extractor, storage, normalizer) is replaceable.
3. **Iterative** — ship working MVP first, add complexity per phase.
4. **Self-discovering** — starts from seed topics, grows organically through Wikipedia link discovery via URL queue.
5. **Determinism wins** — facts only come directly from stored nodes; LLM formats but never invents.

---

## Package Layout

```
hist/
├── __init__.py              # package root
├── config.py                # Neo4j URI, user, password, DB name ("hist")
├── changelog.py             # schema evolution log → data/hist_changelog.json
├── neo4j_driver/
│   ├── __init__.py
│   └── connect.py           # HistDriver singleton, run_cypher / run_cypher_single helpers
├── scraper/
│   ├── __init__.py
│   └── wikipedia.py         # fetch_full_page(url) — wraps Morphos web_fetch with per-request throttle
├── extraction/
│   ├── __init__.py
│   └── extractor.py         # extract_facts(page_text), extract_relations(entities, page_text) via Ollama
├── storage/
│   ├── __init__.py
│   └── store_nodes_edges.py  # store_entity(), store_relation(), batch_ingest(), find_entity(), count_by_type(), delete_entity()
├── normalization/
│   ├── __init__.py
│   └── normalizer.py        # normalize_node_id() canonical dedup, add_alias(), get_canonical() → data/hist_canonical.json
├── url_queue/
│   ├── __init__.py
│   └── queue.py             # add_to_queue(), get_next_url(), mark_completed(), pending_count(), wikipedia_seed(topic) → data/hist_url_queue.json
└── cli/
    └── __init__.py          # [TODO] CLI entry point, end-to-end pipeline runner
```

---

## Node Type Design

Entities use `entity_type` as the discriminator. The field value is capitalized to form the Neo4j label (e.g., `"event"` → `:Event`, `"person"` → `:Person`).

| Base Property | Source | Description |
|---|---|---|
| `node_id` | LLM extraction | lowercase_with_underscores slug (e.g. `ullysses_s_grant`). Unique constraint enforced in Neo4j. |
| `entity_type` | LLM extraction | `"event"` or `"person"`. Drives the Neo4j label via `.capitalize()`. New types emerge organically. |
| `name` | LLM extraction | Canonical display name. |
| `_source_url` | Storage layer | Wikipedia page URL the entity was extracted from (required). |
| `_ingested_at` | Storage layer | Neo4j `toString(timestamp())` — set on every MERGE/SET. |
| **Additional attributes** | LLM extraction | Anything else the LLM extracts (date, location, role, etc.) merged via `n += $props`. |

Entity IDs are normalized through `normalizer.py` which maintains a canonical mapping (`data/hist_canonical.json`) to deduplicate across ingests. New node types and properties are logged in `data/hist_changelog.json`. Phase 7 ships with **event** and **person**. Future phases may add: location, organization, military_command... whatever the LLM surfaces from real pages.

---

## Edge Design

Edges connect two entities by a relationship type extracted from the LLM. The relation string is uppercased and sanitized (spaces/hyphens → underscores) to form the Neo4j relationship type.

```cypher
MATCH (a {node_id: $sid}), (b {node_id: $tid}) CREATE (a)-[:<REL_TYPE>]->(b)
```

The extractor prompts the LLM for `{source_id, target_id, relation_type}` tuples. No preset catalog — types emerge from what the LLM finds in page context (e.g. `PARTICIPATED_IN`, `FOLLOWED_BY`, `PARENT_OF`). Schema shifts are recorded in `data/hist_changelog.json`.

---

## Ingestion Pipeline

```
wikipedia_seed(topic)                    [url_queue/queue.py]
    → add_to_queue(url)   data/hist_url_queue.json

get_next_url()                          [url_queue/queue.py]
    → fetch_full_page(url)              [scraper/wikipedia.py, 3s throttle]
        → extract_facts(page_text[:6000]) [extraction/extractor.py, gemma4:12b via Ollama]
            → normalize_node_id(cand, name) [normalization/normalizer.py → data/hist_canonical.json]
                → store_entity(entity_dict, source_url)  [storage/store_nodes_edges.py]

        → extract_relations(entities, page_text[:6000]) [extraction/extractor.py]
            → store_relation(src_id, tgt_id, rel_type)   [storage/store_nodes_edges.py]

mark_completed(url)                     [url_queue/queue.py]
```

1. **Seed topic** — `wikipedia_seed(topic)` builds Wikipedia URL and queues it in `data/hist_url_queue.json`.
2. **Fetch** — `fetch_full_page(url)` calls Morphos `WebFetch` (Playwright Chrome), 3s throttle between requests, returns up to 6000 chars of page text.
3. **Extract entities** — `extract_facts(page_text)` sends text to Ollama (`gemma4:12b`). Returns list of dicts with `entity_type`, `node_id`, `name`, plus arbitrary attributes (date, location, role). JSON is regex-extracted (`\[[\s\S]*\]`); decode failures return empty list.
4. **Normalize IDs** — `normalize_node_id(candidate_id, name)` checks `data/hist_canonical.json` for existing matches by lowercase comparison. Returns `(canonical_id, is_new)`. Supports alias registration via `add_alias()` and lookup via `get_canonical()`.
5. **Store nodes** — `store_entity(entity_dict, source_url)` does a Neo4j MERGE on `node_id`, SETs all fields as `n += $props` plus `_source_url` + `_ingested_at = toString(timestamp())`. Neo4j label derived from `entity_type.capitalize()` (default `"Event"`).
6. **Extract relations** — `extract_relations(entities, page_text)` sends person/event node lists + text back to LLM for `{source_id, target_id, relation_type}` tuples. Results filtered to require all 3 keys.
7. **Store edges** — `store_relation(source_id, target_id, rel_type)` MATCHes both nodes by `node_id`, CREATEs edge with sanitized type (uppercased, spaces/hyphens → underscores).
8. **Batch ingest** — `batch_ingest(entities, relations)` wraps steps 5+7 in one pass, returns `{created_nodes, updated_existing, edges_written}`.
9. **Queue management** — `get_next_url()` pops first pending URL; `mark_completed(url)` moves it to completed. Both lists deduplicated on save.

## Missing Components (Phase 7 unfinished)

| Component | Status | Notes |
|---|---|---|
| Orchestrator (pipeline glue) | Not coded | Nothing wires scraper → extractor → normalizer → storage together end-to-end |
| Cypher query engine | Not coded | No factual lookup / graph traversal for answering user questions |
| Essay formatter | Not coded | No LLM pass to transform raw graph nodes into essay-format answers |
| CLI entry point | Empty | `hist/cli/__init__.py` is blank, no integration with Morphos multi-agent router |
| Schema bootstrapping | Manual only | DB "hist" and unique constraints on Event/Person created manually; not codified in Python |

## Data Files

| File | Write-by | Format |
|---|---|---|
| `data/hist_url_queue.json` | `url_queue/queue.py` | `{"pending": [...], "completed": [...]}` |
| `data/hist_canonical.json` | `normalization/normalizer.py` | `{variant: {canonical_id, names, first_seen}}` |
| `data/hist_changelog.json` | `changelog.py` | Array of `{timestamp, phase, change_type, details, proposed_by, approved_by}` |

## Truth & Answering Rules

1. **Determinism**: All answers come exclusively from ingested nodes and edges in the Neo4j graph.
2. **No fabrication ever**: If a question can't be grounded in stored data, respond "I don't know" — never guess or make up information.
3. **LLM only formats**: After Cypher traversal retrieves raw facts from Neo4j, LLM transforms them into the requested format (essay, list, timeline). LLM never injects external knowledge at this stage.

## Success Criteria Per Phase

| Phase | Definition of Done | Progress |
|---|---|---|
| 007 | Neo4j DB connects; event + person schemas loaded via Cypher; basic ingestion of a single Wikipedia page works end-to-end | Modules coded, DB created manually. Pipeline glue + CLI not wired — **not done**. |
| 008+ | Evolution rules documented — user-requested changes logged traceably in changelog (auto-approved only with clear documentation) | `changelog.py` coded and functional. |

**Current status:** Individual modules built. Missing orchestrator to wire them together, query engine for factual answers, formatting pass for essays, CLI integration, and codified schema bootstrapping.

