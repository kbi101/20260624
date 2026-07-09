"""Fact extractor — use LLM to identify entities and relationships from Wikipedia text."""

import json
import re

from ollama import Client as OllamaClient

SYSTEM_PROMPT = """You are a fact extraction assistant for HIST (History Information Storage & Truth).
Given scraped Wikipedia article text, extract structured facts. Output ONLY valid JSON matching this shape:
[
  {"entity_type":"event"|"person", "node_id":"<short_slug>", "name":"...", "attribute_name":"value", ...},
]
Rules:
- node_id uses lowercase_with_underscores (e.g., ullysses_s_grant)
- Only extract entities directly mentioned in the text — never invent.
- Include at minimum: entity_type, node_id, name.
- For events include dates if available (as 'date' attribute), locations if mentioned.
- For persons include role/profession if stated."""


def extract_facts(page_text, model="gemma4:12b"):
    """Send page text to LLM and return list of extracted entity dicts."""
    client = OllamaClient()
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": page_text[:6000]},
        ],
    )

    # Extract JSON from LLM response
    text = response.message.content
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


def extract_relations(entities, page_text, model="gemma4:12b"):
    """Ask LLM to identify relationships between extracted entities."""
    if not entities:
        return []

    person_nodes = [(e["node_id"], e["name"]) for e in entities if e.get("entity_type") == "person"]
    event_nodes  = [(e["node_id"], e["name"]) for e in entities if e.get("entity_type") == "event"]

    msg = (
        "These entities were extracted from a Wikipedia article. Identify any direct relationships between them.\n"
        f"People: {person_nodes}\nEvents: {event_nodes}\n"
        "Return ONLY valid JSON array of objects with keys: source_id, target_id, relation_type."
    )

    client = OllamaClient()
    resp = client.chat(model=model, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg}])
    text = resp.message.content
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        rels = json.loads(match.group())
        return [r for r in rels if "source_id" in r and "target_id" in r and "relation_type" in r]
    except json.JSONDecodeError:
        return []
