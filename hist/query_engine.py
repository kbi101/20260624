"""Cypher query engine — hand-written templates with LLM fallback for HIST graph."""

import re
from ollama import Client as OllamaClient
from hist.neo4j_driver.connect import run_cypher, run_cypher_single


LLM_MODEL = "gemma4:12b"


TEMPLATES = [
    {
        "name": "participants_by_id",
        "triggers": ["who", "commanded", "led", "fought"],
        "cypher": (
            "MATCH (e:Event {node_id: $id})-[*1..2]-(p) "
            "RETURN p.node_id AS node_id, p.name AS name, labels(p)[0] AS label"
        ),
    },
    {
        "name": "when_lookup",
        "triggers": ["when", "date", "what year", "which year"],
        "cypher": (
            "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($query) "
            "RETURN n.node_id AS node_id, n.name AS name, n.date AS date, labels(n)[0] AS label "
            "LIMIT 10"
        ),
    },
    {
        "name": "timeline",
        "triggers": ["timeline", "sequence", "order", "chronology", "before", "after", "what happened"],
        "cypher": (
            "MATCH (e:Event) WHERE e.date IS NOT NULL "
            "RETURN e.node_id AS node_id, e.name AS name, e.date AS date "
            "ORDER BY e.date LIMIT 50"
        ),
    },
    {
        "name": "person_details",
        "triggers": ["details", "information", "profile"],
        "cypher": (
            "MATCH (p:Person {node_id: $id}) "
            "RETURN p.node_id AS node_id, p.name AS name, labels(p)[0] AS label, "
            "p.role AS role, p.date AS date, p._source_url AS source_url, p._ingested_at AS ingested"
        ),
    },
    {
        "name": "event_details",
        "triggers": ["tell me", "about"],
        "cypher": (
            "MATCH (e:Event {node_id: $id}) "
            "RETURN e.node_id AS node_id, e.name AS name, labels(e)[0] AS label, "
            "e.date AS date, e._source_url AS source_url, e._ingested_at AS ingested"
        ),
    },
    {
        "name": "relationships",
        "triggers": ["connected", "links", "relationship", "relations", "network"],
        "cypher": (
            "MATCH (a)-[r]->(b) WHERE a.node_id = $id OR b.node_id = $id "
            "RETURN a.node_id AS src, type(r) AS rel, b.node_id AS tgt LIMIT 30"
        ),
    },
    {
        "name": "family_tree",
        "triggers": ["parent", "child", "family", "ancestor", "descendant"],
        "cypher": (
            "MATCH (p:Person {node_id: $id})-[*1..5]-(r) "
            "RETURN DISTINCT r.node_id AS node_id, r.name AS name, labels(r)[0] AS label"
        ),
    },
    {
        "name": "all_events",
        "triggers": ["events", "list events"],
        "cypher": (
            "MATCH (e:Event) "
            "RETURN e.node_id AS node_id, e.name AS name, e.date AS date "
            "ORDER BY e.date LIMIT 60"
        ),
    },
    {
        "name": "fulltext_search",
        "triggers": [],
        "cypher": (
            "MATCH (n) WHERE toLower(n.name) CONTAINS $query OR "
            "(n.date IS NOT NULL AND n.date CONTAINS $query) "
            "RETURN DISTINCT n.node_id AS node_id, n.name AS name, labels(n)[0] AS label, n.date AS date "
            "LIMIT 30"
        ),
    },
]


def _extract_entity(query):
    """Pull a person or event slug from the question text.

    Handles both 'Battle of Gettysburg' and 'gettysburg'.
    """
    m = re.search(
        r"(?:the\s+)?(?:battle|siege|war|event)\s+(?:of|at)?\s+"
        r'"?([A-Za-z][\w\s\'\-&\.]+)"',
        query,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower().replace(" ", "_")

    words = re.findall(r"[A-Z][a-zA-Z']{2,}", query)
    if len(words) >= 2:
        return " ".join(words).lower().replace(" ", "_")

    single_cap = re.findall(r"\b[A-Z][a-zA-Z']{2,}\b", query)
    if single_cap:
        return single_cap[0].lower()

    return None


def _match_template(query):
    """Find the best matching template. Falls back to fulltext_search."""
    low = query.lower()
    for tpl in TEMPLATES[:-1]:
        if any(kw in low for kw in tpl["triggers"]):
            return tpl

    last = TEMPLATES[-1]
    if re.search(r"\w+", low):
        return last
    return None


def _search_term_params(query):
    """Return parameters dict with the best search term: first significant word."""
    stop_words = {
        "who", "what", "when", "where", "which", "the", "a", "an", "and", "or",
        "of", "in", "do", "does", "did", "is", "was", "tell", "me", "about",
    }
    words = re.findall(r"\b\w{3,}\b", query.lower())
    terms = [w for w in words if w not in stop_words]
    return {
        "query": (terms[0] if terms else query[:60]),          # single best term for CONTAINS
        "all_terms": [t.strip() for t in terms] or [query[:60]],  # all significant terms
    }


def execute_template(tpl, query):
    """Run a matched template with inferred parameters."""
    entity_id = _extract_entity(query)

    params = {}
    if "$id" in tpl["cypher"]:
        params["id"] = entity_id or ""
        if not params["id"]:
            return []

    search = _search_term_params(query)
    if "$query" in tpl["cypher"]:
        params["query"] = search["query"]

    # For fulltext_search, try each significant term individually since CONTAINS only matches one substring.
    terms_to_try = None
    if tpl.get("name") == "fulltext_search":
        terms_to_try = list(set(search["all_terms"]))

    for t in (terms_to_try or [params.get("query", "")]):
        try:
            p = dict(params)
            p["query"] = t
            results = run_cypher(tpl["cypher"], p)
            if results:
                return results
        except Exception:
            continue

    return []


CYPHER_GEN_SYSTEM = (
    "You generate Cypher for a Neo4j graph of historical Events and Persons.\n"
    "Properties: node_id, name, date (events), role (persons), _source_url.\n"
    "Edge types: PARTICIPANT, FOLLOWED_BY etc.\n"
    "Answer with ONE Cypher query. Use MATCH-WHERE-RETURN structure.\n"
    "Use parameter $query for text search."
)


def llm_cypher_fallback(query):
    """Generate Cypher via LLM when templates return empty."""
    prompt = f'Question: "{query}"\n\nCypher:'
    try:
        client = OllamaClient()
        resp = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": CYPHER_GEN_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        cypher_text = resp.message.content.strip()
    except Exception:
        return []

    cypher_text = re.sub(r"^```(?:cypher|sql)?\n?", "", cypher_text, flags=re.IGNORECASE)
    cypher_text = re.sub(r"\n```$", "", cypher_text, flags=re.IGNORECASE).strip()

    params = {
        "query": _search_term_params(query)["query"],
        "id": _extract_entity(query) or "",
    }

    for retry in range(2):
        try:
            results = run_cypher(cypher_text, params)
            if results:
                return results
        except Exception as exc:
            if retry == 0:
                client = OllamaClient()
                r2 = client.chat(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": CYPHER_GEN_SYSTEM},
                        {"role": "user", "content": f"{prompt}\n\nError: {exc}\nFixed Cypher:"},
                    ],
                )
                cypher_text = r2.message.content.strip()
                cypher_text = re.sub(r"^```(?:cypher|sql)?\n?", "", cypher_text, flags=re.IGNORECASE)
                cypher_text = re.sub(r"\n```$", "", cypher_text, flags=re.IGNORECASE).strip()
            else:
                return []

    return []


def ask(query):
    """Run the full query pipeline. Returns list of result dicts or None."""
    tpl = _match_template(query)
    if not tpl:
        return None

    results = execute_template(tpl, query)
    if results:
        return results

    fallback = llm_cypher_fallback(query)
    return fallback or None


def get_graph_data(query=None, hop_depth=1, max_nodes=80):
    """Return a subgraph for the timeline frontend.

    If query is given, seed on matching nodes and expand hop_depth hops.
    If query is None, return the last `max_nodes // 2` events by date.
    Caps total returned nodes to max_nodes so the browser never chokes.
    """

    if query:
        # Step 1 — find seed nodes matching the query
        seeds = run_cypher(
            "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($q) "
            "RETURN n.node_id AS node_id, labels(n)[0] AS label "
            f"LIMIT {max_nodes // 3}",
            {"q": query},
        )
        if not seeds:
            return {"events": [], "persons": [], "edges": []}

        seed_ids = [r["node_id"] for r in seeds]

        # Step 2 — expand hop_depth hops from seeds (use literal depth)
        all_nodes_cur = run_cypher(
            f"UNWIND $ids AS sid MATCH (start {{node_id: sid}}) "
            f"MATCH path = (start)-[*0..{int(hop_depth)}]-(neighbour) "
            f"RETURN DISTINCT neighbour.node_id AS node_id, "
            f"       labels(neighbour)[0] AS label",
            {"ids": seed_ids},
        )

        expanded_ids = [r["node_id"] for r in all_nodes_cur][:max_nodes]
    else:
        # Default: most recent events
        recent = run_cypher(
            "MATCH (e:Event) WHERE e.date IS NOT NULL "
            "RETURN e.node_id AS node_id, labels(e)[0] AS label "
            "ORDER BY e.date DESC LIMIT $limit",
            {"limit": max_nodes // 2},
        )
        expanded_ids = [r["node_id"] for r in recent]

    if not expanded_ids:
        return {"events": [], "persons": [], "edges": []}

    # Step 3 — fetch properties for the selected nodes
    events_cur = run_cypher(
        "UNWIND $ids AS nid MATCH (e:Event {node_id: nid}) "
        "RETURN e.node_id AS node_id, e.name AS name, "
        "e.date AS date, e._source_url AS source_url",
        {"ids": expanded_ids},
    )

    persons_cur = run_cypher(
        "UNWIND $ids AS nid MATCH (p:Person {node_id: nid}) "
        "RETURN p.node_id AS node_id, p.name AS name, "
        "p._source_url AS source_url",
        {"ids": expanded_ids},
    )

    # Step 4 — edges only between selected nodes
    edges_cur = run_cypher(
        "MATCH (a)-[r]->(b) WHERE a.node_id IN $ids AND b.node_id IN $ids "
        "RETURN a.node_id AS src, type(r) AS rel, b.node_id AS tgt",
        {"ids": expanded_ids},
    )

    ev_list = []
    for rec in events_cur:
        d = rec.get("date") or ""
        year_m = re.search(r"\b(\d{4})\b", str(d))
        e = {
            "node_id": rec["node_id"],
            "name": rec["name"],
            "date": str(d) if d else "",
            "year": int(year_m.group(1)) if year_m else None,
            "source_url": str(rec.get("source_url") or ""),
        }
        ev_list.append(e)

    per_list = []
    for rec in persons_cur:
        per_list.append({
            "node_id": rec["node_id"],
            "name": rec["name"],
            "source_url": str(rec.get("source_url") or ""),
        })

    ed_list = []
    for rec in edges_cur:
        ed_list.append({
            "src": rec.get("src", ""),
            "rel": rec.get("rel", ""),
            "tgt": rec.get("tgt", ""),
        })

    return {"events": ev_list, "persons": per_list, "edges": ed_list}


def get_node_details(node_id):
    """Full properties + connected edges for a given node."""
    props_rec = run_cypher_single(
        "MATCH (n {node_id: $id}) RETURN n AS all_props",
        {"id": node_id},
    )

    if not props_rec or not props_rec.get("all_props"):
        return None

    ap = props_rec["all_props"] or {}
    if hasattr(ap, "keys") and hasattr(ap, "values"):
        ap_dict = {k: str(v) for k, v in ap.items()}
        label_val = ap_dict.pop("_labels", "")
    else:
        ap_dict = {}
        label_val = ""

    connections = run_cypher(
        "MATCH (a)-[r]->(b) WHERE a.node_id=$id OR b.node_id=$id "
        "RETURN a.node_id AS src, type(r) AS rel, b.node_id AS tgt",
        {"id": node_id},
    )

    return {
        "label": label_val,
        "node_id": ap_dict.get("node_id", node_id),
        "name": ap_dict.get("name", ""),
        "props": ap_dict,
        "connections": connections,
    }
