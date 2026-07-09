"""Evidence-to-answer LLM formatter for HIST queries."""

import json
from ollama import Client as OllamaClient

LLM_MODEL = "gemma4:12b"


def _nodes_to_evidence(raw):
    """Convert raw Cypher result dicts to a readable evidence block."""
    lines = []
    for i, rec in enumerate(raw, 1):
        parts = []
        if "name" in rec:
            label_val = rec.get("label", "")
            if hasattr(label_val, "__iter__") and not isinstance(label_val, str):
                label_val = label_val[0] if label_val else ""
            parts.append(f"{rec['name']} ({label_val})")
        if "date" in rec:
            d = rec["date"]
            if hasattr(d, "__iter__") and not isinstance(d, str):
                try:
                    d = d[0]
                except Exception:
                    d = None
            if d:
                parts.append(f"{d}")
        if "src" in rec and "tgt" in rec:
            parts.append(f"{rec['src']} --[{rec.get('rel', 'related')}]--> {rec['tgt']}")
        if parts:
            lines.append(f"  [{i}] {' | '.join(parts)}")
    return "\n".join(lines)


def format_answer(question, raw_results):
    """Take query results and produce a grounded natural-language answer.

    Returns dict with keys: answer (str), nodes_used (int), edges_used (int).
    """
    if not raw_results:
        return {"answer": "No matching data in the graph.", "nodes_used": 0, "edges_used": 0}

    evidence = _nodes_to_evidence(raw_results)
    has_edges = any("src" in r and "tgt" in r for r in raw_results)
    nodes_count = len(raw_results) if not has_edges else 0
    edges_count = len(raw_results) if has_edges else 0

    evidence_block = f"Evidence from graph: {nodes_count} entries\n{evidence}"

    system_prompt = (
        "You are a history Q&A assistant that answers ONLY from the provided graph evidence.\n"
        "Rules:\n"
        "- Use only facts listed in the Evidence block above.\n"
        "- Cite sources inline like [1], [2] referencing the evidence list.\n"
        "- If the question cannot be answered from evidence, say 'I do not have that information in my graph.'\n"
        "- Do not invent, extrapolate, or add outside knowledge.\n"
        "- Keep answers concise: 2-4 sentences for direct questions, up to a short paragraph for open-ended ones.\n"
        "- End with a 'Sources:' line listing the Wikipedia URLs if available in evidence.\n"
        "Output ONLY the answer text."
    )

    try:
        client = OllamaClient()
        resp = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Question: {question}\n\n{evidence_block}"
                )},
            ],
        )
        answer = resp.message.content.strip()[:2000]
    except Exception:
        answer = _fallback_answer(question, raw_results)

    return {"answer": answer, "nodes_used": max(nodes_count, 1), "edges_used": edges_count}


def _fallback_answer(question, raw_results):
    """If LLM unavailable, produce a basic list from the raw nodes."""
    lines = [f'Here is what I found for "{question}":']
    seen_names = set()
    for rec in raw_results[:20]:
        if "name" in rec and rec["name"] not in seen_names:
            label_part = f" ({rec.get('label', '')})" if rec.get("label") else ""
            date_part = f", {rec['date']}" if rec.get("date") else ""
            lines.append(f"- {rec['name']}{label_part}{date_part}")
            seen_names.add(rec["name"])
    return "\n".join(lines)
