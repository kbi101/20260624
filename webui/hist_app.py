"""FastAPI routes for HIST query engine + orchestrator."""

import asyncio
import json
import os
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(prefix="/api/hist", tags=["hist"])

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "static")


class AskRequest(BaseModel):
    question: str


class SeedRequest(BaseModel):
    topic: str


@router.get("/graph-data")
async def get_graph_data(query: str = None, hops: int = 1, limit: int = 80):
    """Return a subgraph — optional search query, hop depth, and node cap."""
    from hist.query_engine import get_graph_data as _get_gd
    data = await asyncio.to_thread(_get_gd, query=query, hop_depth=hops, max_nodes=limit)
    return JSONResponse(content=data)


@router.get("/node-details/{node_id}")
async def get_node_details(node_id: str):
    """Return full properties + connected edges for a node."""
    from hist.query_engine import get_node_details as _get_nd
    data = await asyncio.to_thread(_get_nd, node_id)
    return JSONResponse(content=data or {"error": "node not found"})


@router.post("/ask")
async def ask_question(req: AskRequest):
    """Ask a history question against the graph."""
    from hist.query_engine import ask as _ask
    from hist.formatter import format_answer as _fmt

    raw = await asyncio.to_thread(_ask, req.question)

    if not raw:
        return JSONResponse(content={
            "answer": "No matching data in the graph. Try ingesting more topics.",
            "nodes_used": 0,
            "edges_used": 0,
            "evidence": [],
            "suggestion": None,
        })

    nodes_count = len(raw) if "src" not in raw[0] else 0
    edges_count = len(raw) if "src" in raw[0] else 0

    ans = await asyncio.to_thread(_fmt, req.question, raw)
    return JSONResponse(content={
        "answer": ans["answer"],
        "nodes_used": max(nodes_count, ans.get("nodes_used", 1)),
        "edges_used": ans.get("edges_used", edges_count),
        "evidence": raw[:50],
    })


@router.post("/ingest")
async def ingest_topic(req: SeedRequest):
    """Seed a topic and ingest the corresponding Wikipedia page."""
    from hist.url_queue.queue import wikipedia_seed
    from hist.orchestrator import ingest_page

    url = wikipedia_seed(req.topic)
    result = await asyncio.to_thread(ingest_page, url)
    return JSONResponse(content={"status": "done", "result": result, "url": url})


@router.post("/ingest-queue")
async def ingest_queue():
    """Process all pending URLs in the queue."""
    from hist.orchestrator import ingest_queue as _inq

    results = await asyncio.to_thread(_inq, run_all=True)
    return JSONResponse(content={"status": "done", "results": results})


@router.get("/stats")
async def get_stats():
    """Return current node/edge counts."""
    from hist.orchestrator import graph_stats
    data = await asyncio.to_thread(graph_stats)
    return JSONResponse(content=data)


@router.get("/expand-node/<node_id>/")
async def expand_node(node_id: str, hops: int = 1):
    """Return the expanded neighbourhood of a clicked node."""
    from hist.neo4j_driver.connect import run_cypher

    # Consume the result list from run_cypher before reusing IDs
    neighbours_raw = [rec for rec in run_cypher(
        f"MATCH path = (n {{node_id: $id}})-[*1..{int(hops)}]-(neighbour) "
        "RETURN DISTINCT neighbour.node_id AS node_id, neighbour.name AS name, labels(neighbour)[0] AS label",
        {"id": node_id},
    )]


    neigh_ids = [dict(r)["node_id"] for r in neighbours_raw]

    edges_raw = [rec for rec in run_cypher(
        "MATCH (a)-[r]->(b) WHERE "
        "(a.node_id = $id AND b.node_id IN $neighs) OR "
        "(b.node_id = $id AND a.node_id IN $neighs) "
        "RETURN a.node_id AS src, type(r) AS rel, b.node_id AS tgt",
        {"id": node_id, "neighs": neigh_ids},
    )]

    return JSONResponse(content={
        "seed_id": node_id,
        "neighbours": neighbours_raw,
        "edges": edges_raw,
    })


@router.get("/")
async def hist_page():
    """Serve the HIST dashboard page."""
    html_path = Path(_TEMPLATE_DIR) / "hist_index.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>HIST Dashboard</h1><p>Loading...</p>")
    return HTMLResponse(content=html_path.read_text())
