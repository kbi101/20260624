"""FastAPI server that hosts the web UI for morphos Cognitive Dashboard."""

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Morphos Cognitive Dashboard")
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(os.path.join(_FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

from webui.hist_app import router as hist_router
app.include_router(hist_router)

_uct_depth = 1
_uct_mode = "understand"
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "static")
_HISTORY_DIR = Path(os.path.join(os.path.dirname(__file__), "..", "data", "dashboard_history")).resolve()


class TopicRequest(BaseModel):
    topic: str
    depth: int = 1
    mode: str = "understand"


def _build_engine(depth: int, mode: str):
    from morphos.config import Config
    from morphos.llm import LLMClient
    from uct.engine import UCTEngine

    config = Config(model="gemma4:12b")
    config.uct_depth = depth
    config.uct_mode = mode
    llm = LLMClient(model="gemma4:12b", config=config)
    return UCTEngine(llm, depth=depth, mode=mode), config


def _topic_to_filename(topic: str) -> str:
    """Create a safe filename from a topic string."""
    import re as _re
    sanitized = _re.sub(r'[^\w\s-]', '', topic).strip().lower()
    sanitized = _re.sub(r'\s+', '-', sanitized)
    return sanitized[:120]


def _history_index_path(topic: str) -> Path:
    """Get the metadata index file path for a topic."""
    return _HISTORY_DIR / (f"{_topic_to_filename(topic)}.json")


def _load_cached(topic: str):
    """Load cached dashboard data by topic name. Tries exact match, then filename match."""
    primary = _history_index_path(topic)
    if primary.exists():
        try:
            meta = json.loads(primary.read_text())
            content_file = Path(meta.get("content_path", ""))
            refs_file = Path(meta.get("refs_path", ""))
            data = json.loads(content_file.read_text()) if content_file.exists() else None
            refs = json.loads(refs_file.read_text()) if refs_file.exists() else []
            if data:
                return data, refs
        except Exception:
            pass

    fuzzy_match = _HISTORY_DIR / (_topic_to_filename(topic) + ".json")
    if fuzzy_match != primary and fuzzy_match.exists():
        return _load_cached_direct(fuzzy_match)

    content_file = _HISTORY_DIR / (f"{_topic_to_filename(topic)}_content.json")
    refs_file = _HISTORY_DIR / (f"{_topic_to_filename(topic)}_refs.json")
    if content_file.exists():
        try:
            data = json.loads(content_file.read_text())
            refs = json.loads(refs_file.read_text()) if refs_file.exists() else []
            return data, refs
        except Exception:
            pass

    return None, None


def _load_cached_direct(idx_path: Path):
    """Load dashboard data from an index file path."""
    try:
        meta = json.loads(idx_path.read_text())
        content_file = Path(meta.get("content_path", ""))
        refs_file = Path(meta.get("refs_path", ""))
        data = json.loads(content_file.read_text()) if content_file.exists() else None
        refs = json.loads(refs_file.read_text()) if refs_file.exists() else []
        return data, refs
    except Exception:
        return None, None


def _has_cached(topic: str) -> bool:
    """Check if any cache exists for this topic (exact or filename-based)."""
    data, _ = _load_cached(topic)
    return data is not None


def _save_cached(topic: str, data: dict, refs: list):
    """Save dashboard data and metadata to disk for history persistence."""
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    fname = _topic_to_filename(topic)
    content_path = _HISTORY_DIR / f"{fname}_content.json"
    refs_path = _HISTORY_DIR / f"{fname}_refs.json"

    content_path.write_text(json.dumps(data))
    refs_path.write_text(json.dumps(refs))

    idx = _history_index_path(topic)
    meta = {
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_path": str(content_path),
        "refs_path": str(refs_path),
    }
    if idx.exists():
        old = json.loads(idx.read_text())
        old["content_path"] = meta["content_path"]
        old["refs_path"] = meta["refs_path"]
        old["timestamp"] = meta["timestamp"]
        idx.write_text(json.dumps(old))
    else:
        meta["created"] = datetime.now(timezone.utc).isoformat()
        idx.write_text(json.dumps(meta))


def _list_history() -> list[dict]:
    """List all saved dashboard topics sorted by most recent."""
    if not _HISTORY_DIR.exists():
        return []
    entries = []
    for f in sorted(_HISTORY_DIR.glob("*.json")):
        if f.name.endswith("_content.json") or f.name.endswith("_refs.json"):
            continue
        try:
            meta = json.loads(f.read_text())
            entries.append({
                "topic": meta.get("topic", f.stem),
                "timestamp": meta.get("created", ""),
            })
        except Exception:
            continue
    return sorted(entries, key=lambda e: e["timestamp"], reverse=True)[:]


def _fetch_page_plain(url: str) -> str:
    """Fetch a webpage using plain requests (no Playwright, safe inside asyncio)."""
    import requests as _req
    from bs4 import BeautifulSoup as _BS

    headers = {"User-Agent": "Mozilla/5.0 Chrome/125.0"}
    try:
        resp = _req.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = _BS(resp.text, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else url[:80])
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l.strip()]
        return f"[{title}]\n" + "\n".join(lines)[:6000]
    except Exception as ex:
        return f"[Fetch failed]\nError: {ex}"


def _parse_ddg_redirect(href: str) -> str:
    """Extract the real URL from a DDG redirect link like //duckduckgo.com/l/?uddg=..."""
    if href.startswith("http"):
        return href
    from urllib.parse import unquote, urlparse, parse_qs
    parsed = urlparse("https:" + href if href.startswith("//") else href)
    params = parse_qs(parsed.query)
    if "uddg" in params:
        return unquote(params["uddg"][0])
    return href


def _search_ddg_plain(topic: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Search DuckDuckGo via plain HTTP. Returns ([(title, url), ...], [snippets])."""
    import requests as _req
    from urllib.parse import quote_plus

    headers = {"User-Agent": "Mozilla/5.0 Chrome/125.0"}
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(topic)}"
        resp = _req.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return [], []

        from bs4 import BeautifulSoup as _BS
        soup = _BS(resp.text, "html.parser")
        results = []

        for result_div in soup.select(".result")[:8]:
            title_el = result_div.select_one(".result__title")
            link_el = result_div.select_one("a.result__url, .links_main a")
            if not title_el or not link_el:
                continue
            text = title_el.get_text(strip=True)
            href = _parse_ddg_redirect(link_el.get("href", ""))
            if href.startswith("http") and len(text) > 5:
                results.append((text[:200], href))

        snippets = [p.get_text(strip=True)[:300] for p in soup.select(".result__snippet, .result__body a:last-of-type")[:8]]
        return results, snippets
    except Exception:
        return [], []


def _gather_research(topic: str):
    """Search + fetch top results. Returns (context_str, [(title, url), ...])."""
    links, snippets = _search_ddg_plain(topic)

    seen_urls = set()
    unique_links = []
    for title, url in links:
        clean = url.split("?")[0] if "?" in url else url
        if clean not in seen_urls:
            seen_urls.add(clean)
            unique_links.append((title, url))

    urls_info = []
    parts = []

    for idx, (title, url) in enumerate(unique_links[:3]):
        page = _fetch_page_plain(url)
        tm = re.search(r'\[(.+?)\]', page)
        fetched_title = tm.group(1) if tm else title
        content = ""
        if tm:
            rest = page[len(tm.group(0)):]
            content = rest.strip() if rest.strip() else (snippets[idx] if idx < len(snippets) else "")

        urls_info.append((fetched_title, url))
        parts.append((content or "")[:2000].strip())

    for idx, snippet in enumerate(snippets[:3]):
        if idx < len(parts) and parts[idx] == "":
            parts[idx] = snippet

    # If no pages fetched but we have snippets, use them directly
    if not parts and snippets:
        parts = [s[:2000] for s in snippets[:3]]

    return "\n\n".join(parts), urls_info


def _model_to_dict(model):
    """Convert TopicModel to a JSON-serializable dict for the frontend."""
    from uct.graph import KnowledgeGraph

    dims = {}
    if model.dimension_profile:
        dims = model.dimension_profile.as_dict()
        dims["dominant"] = model.dimension_profile.dominant
        dims["primary_concepts"] = model.dimension_profile.primary_concepts

    concepts = []
    for c in model.concepts:
        concepts.append({
            "name": c.name,
            "definition": c.definition,
            "why_it_exists": c.why_it_exists,
            "constraints": c.constraints,
            "failure_modes": c.failure_modes,
        })

    scaled = []
    for sc in model.scaled_concepts:
        matched = next((c for c in model.concepts if c.name == sc.concept.name), None)
        cn = sc.concept.name
        df = sc.concept.definition or (matched.definition if matched else "")
        scaled.append({
            "name": cn,
            "definition": df[:200],
            "scale": sc.scale,
        })

    seqs = []
    for sb in model.sequence_blocks:
        steps = [{"label": s.label, "input": s.input, "transformation": s.transformation,
                 "validation": s.validation, "output": s.output,
                 "failure_condition": s.failure_condition,
                 "prerequisites": s.prerequisites} for s in sb.steps]
        seqs.append({"title": sb.title, "steps": steps})

    loops = []
    for cl in model.causal_loops:
        links = [{"from": l.from_node, "to": l.to_node, "effect": l.effect,
                  "delay": l.delay} for l in cl.links]
        loops.append({"title": cl.title, "loops": cl.loops, "links": links,
                      "loop_type": cl.loop_type})

    matrices = []
    for mx in model.matrices:
        cells = {f"{k[0]}|{k[1]}": v for k, v in mx.cells.items()}
        matrices.append({"title": mx.title, "attributes": mx.attributes,
                         "options": mx.options, "cells": cells})

    edges = [{"from": e.from_node, "to": e.to_node, "type": e.edge_type}
             for e in model.edges]

    compressions = []
    for comp in model.compressions:
        compressions.append({
            "concept_name": comp.concept_name,
            "level_0_essence": comp.level_0_essence,
            "level_1_functional": comp.level_1_functional,
            "level_2_detailed": comp.level_2_detailed,
            "level_3_expert": comp.level_3_expert,
        })

    # Build graph adjacency for frontend
    g = KnowledgeGraph()
    for c in model.concepts:
        g.add_node(c.name)
    if model.edges:
        g.add_edges(model.edges)
    adj = {}
    for node_name in list(g.nodes):
        conns = g.all_connections(node_name)
        adj[node_name] = [{"name": cn, "edge_type": et} for cn, et, _dir in conns]

    return {
        "topic": model.topic,
        "dimensions": dims,
        "concepts": concepts,
        "scaled_concepts": scaled,
        "sequence_blocks": seqs,
        "causal_loops": loops,
        "matrices": matrices,
        "edges": edges,
        "compressions": compressions,
        "graph": {"nodes": list(g.nodes), "adjacency": adj},
    }


def _read_dashboard_template():
    """Read dashboard HTML template once at startup."""
    with open(os.path.join(_TEMPLATE_DIR, "dashboard.html")) as f:
        return f.read()

_DASHBOARD_TEMPLATE = None  # lazy init on first request


def _render_html(data_dict, ref_urls, topic):
    global _DASHBOARD_TEMPLATE
    if _DASHBOARD_TEMPLATE is None:
        _DASHBOARD_TEMPLATE = _read_dashboard_template()

    js_data = json.dumps(data_dict)
    if ref_urls and isinstance(ref_urls[0], dict):
        refs_json = json.dumps(ref_urls)
    else:
        refs_json = json.dumps([{"title": t, "url": u} for t, u in ref_urls])
    safe_topic = topic.replace('"', '&quot;')

    return _DASHBOARD_TEMPLATE.replace("{{data}}", js_data).replace("{{refs}}", refs_json).replace("{{topic}}", safe_topic)


def _generate_full(topic: str, depth: int, mode: str):
    """Blocking work: research + generate + serialize. Runs off the asyncio loop."""
    cached_data, cached_refs = _load_cached(topic)
    if cached_data and cached_refs is not None and cached_data.get("concepts"):
        return cached_data, cached_refs

    engine, cfg = _build_engine(depth, mode)
    research_ctx, ref_urls = _gather_research(topic)
    _, model = engine.generate_dashboard(topic, research_context=research_ctx)
    data = _model_to_dict(model)
    refs_json = [{"title": t, "url": u} for t, u in ref_urls]
    _save_cached(topic, data, refs_json)
    return data, ref_urls


@app.get("/hist", response_class=HTMLResponse)
async def hist_page():
    """Serve the HIST history graph page or React SPA."""
    react_index = os.path.join(_FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        with open(react_index) as f:
            return f.read()
    hp = os.path.join(_TEMPLATE_DIR, "hist_index.html")
    if os.path.exists(hp):
        with open(hp) as f:
            return f.read()
    return HTMLResponse(content="<h1>HIST</h1><p>Page not found.</p>")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main React Motion UI dashboard page."""
    react_index = os.path.join(_FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        with open(react_index) as f:
            return f.read()
    with open(os.path.join(_TEMPLATE_DIR, "index.html")) as f:
        return f.read()


@app.post("/api/dashboard", response_class=HTMLResponse)
async def generate_dashboard(request: TopicRequest):
    """Generate a full topic model and serve it on the web dashboard."""
    data, ref_urls = await asyncio.to_thread(
        _generate_full, request.topic, request.depth, request.mode
    )
    return HTMLResponse(content=_render_html(data, ref_urls, request.topic))


@app.post("/api/regenerate", response_class=HTMLResponse)
async def regenerate_dashboard(request: TopicRequest):
    """Force regenerate a topic, bypassing the cache."""
    idx = _history_index_path(request.topic)
    idx.unlink(missing_ok=True)
    content_f = _HISTORY_DIR / (_topic_to_filename(request.topic) + "_content.json")
    refs_f = _HISTORY_DIR / (_topic_to_filename(request.topic) + "_refs.json")
    content_f.unlink(missing_ok=True)
    refs_f.unlink(missing_ok=True)

    data, ref_urls = await asyncio.to_thread(
        _generate_full, request.topic, request.depth, request.mode
    )
    return HTMLResponse(content=_render_html(data, ref_urls, request.topic))


@app.get("/api/data", response_class=HTMLResponse)
async def get_dashboard(topic: str = Query(...), depth: int = 1, mode: str = "understand"):
    """GET endpoint that generates and serves the dashboard."""
    data, ref_urls = await asyncio.to_thread(_generate_full, topic, depth, mode)
    return HTMLResponse(content=_render_html(data, ref_urls, topic))


@app.get("/api/json")
async def json_api(topic: str = Query(...), depth: int = 1, mode: str = "understand"):
    """Return raw JSON dashboard data."""
    data, ref_urls = await asyncio.to_thread(_generate_full, topic, depth, mode)
    return {**data, "references": [{"title": t, "url": u} for t, u in ref_urls]}


@app.get("/api/history")
async def list_history():
    """Return list of all saved dashboard topics."""
    return await asyncio.to_thread(_list_history)


@app.get("/api/history/{topic}")
async def load_cached_topic(topic: str):
    """Load a cached dashboard from history."""
    data, refs = await asyncio.to_thread(_load_cached, topic)
    if data and refs is not None:
        return HTMLResponse(content=_render_html(data, refs, topic))
    return {"error": "Topic not found in history"}


@app.post("/api/history/{topic}")
async def reload_and_regenerate(topic: str):
    """Force regenerate a topic from history, even if cached."""
    idx = _history_index_path(topic)
    if idx.exists():
        old = json.loads(idx.read_text())
        data_f = Path(old.get("content_path", ""))
        refs_f = Path(old.get("refs_path", ""))
        cmeta_f = Path(str(data_f)) if data_f.suffix == ".json" and data_f.name.endswith("_content.json") else None
    else:
        return {"error": "Topic not found"}

    tmp_path = _history_index_path(topic)
    tmp_path.unlink(missing_ok=True)

    data, ref_urls = await asyncio.to_thread(_generate_full, topic, 1, "understand")
    refs_json = [{"title": t, "url": u} for t, u in ref_urls]
    _save_cached(topic, data, refs_json)
    return {
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.delete("/api/history/{topic}")
async def clear_history_entry(topic: str):
    """Delete a saved dashboard from history."""
    idx = _history_index_path(topic)
    deleted = False
    if idx.exists():
        meta = json.loads(idx.read_text())
        for key in ("content_path", "refs_path"):
            p = Path(meta.get(key, ""))
            if p.exists():
                p.unlink()
                deleted = True
        idx.unlink()
        deleted = True
    return {"deleted": deleted}


@app.delete("/api/history")
async def clear_all_history():
    """Delete all saved dashboards."""
    import shutil as _shutil
    removed = []
    if _HISTORY_DIR.exists():
        for f in sorted(_HISTORY_DIR.glob("*.json")):
            f.unlink()
            removed.append(f.name)
    return {"cleared": len(removed)}
