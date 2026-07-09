"""Normalization + deduplication across multi-source Wikipedia ingests."""

import json, os
from datetime import datetime

CANONICAL_PATH = "data/hist_canonical.json"


def _load_map():
    if os.path.exists(CANONICAL_PATH):
        with open(CANONICAL_PATH) as f:
            return json.load(f)
    return {}


def _save_map(m):
    with open(CANONICAL_PATH, "w") as f:
        json.dump(m, f, indent=2)


def normalize_node_id(candidate_id, name):
    """Given a raw node_id candidate from LLM extraction, return the canonical ID.

    If this entity was seen before under a slightly different ID, merge to existing record. Otherwise create new entry.
    Returns (canonical_node_id, is_new: bool).
    """
    mapping = _load_map()
    # Check approximate match by lowercase comparison
    key = candidate_id.lower().replace("-", "_").replace(" ", "_")

    for old_key, data in list(mapping.items()):
        if old_key == key or old_key == name.lower().replace(" ", "_"):
            return data["canonical_id"], False

    # New entity — register it
    mapping[candidate_id.lower()] = {
        "canonical_id": key,
        "names": [name],
        "first_seen": datetime.utcnow().isoformat(),
    }
    _save_map(mapping)
    return key, True


def add_alias(node_id, variant):
    """Record a variant name/ID pointing to the same canonical entity."""
    mapping = _load_map()
    canon_key = node_id.lower().replace("-", "_").replace(" ", "_")

    # Find existing entry  
    for k, d in list(mapping.items()):
        if d["canonical_id"] == canon_key:
            d["names"].append(variant)
            mapping[variant.lower().replace(" ", "_")] = d  # alias maps back to same dict
            _save_map(mapping)
            return

    # Register fresh
    mapping[canon_key] = {
        "canonical_id": canon_key,
        "names": [variant],
        "first_seen": datetime.utcnow().isoformat(),
    }
    _save_map(mapping)


def get_canonical(variant):
    """Look up canonical ID from any variant."""
    mapping = _load_map()
    key = variant.lower().replace("-", "_").replace(" ", "_")
    entry = mapping.get(key, None) or next((v for k, v in mapping.items() if v["canonical_id"] == key), None)
    return entry["canonical_id"] if entry else key
