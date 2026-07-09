"""Persistent change-log for schema & structural evolution."""

import json, os
from datetime import datetime, timezone

CHANGELOG_PATH = "data/hist_changelog.json"


def _load():
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH) as f:
            return json.load(f)
    return []


def append(phase, change_type, details, proposed_by="user", approved_by="user"):
    """Record a schema/structural change."""
    entries = _load()
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": str(phase),
        "change_type": change_type,
        "details": details,
        "proposed_by": proposed_by,
        "approved_by": approved_by,
    })
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def recent(n=5):
    """Return the n most recent changelog entries."""
    return _load()[-n:]
