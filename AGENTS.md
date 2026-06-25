# Morphos Project Rules

## ⚠️ READ PROJECT_STATUS.md FIRST

Before doing anything, read `PROJECT_STATUS.md` at the project root. It contains:
- All 4 working tools and their backends
- Which network services are blocked from this IP (Google, DDGS library, Yahoo Finance)
- What actually works (DuckDuckGo main site via Chrome, weather.gov, yfinance)

## AUTO-LOG CONVERSATIONS (ALWAYS)

After every response you give to the user, append the exchange to `conversations.md` at the project root.

### Format

Append at the bottom:

```md
## <ISO 8601 timestamp> - <topic title>

**Q:** <brief summary of user's question/request>
**A:** <brief summary of what you answered/did>
```

### Rules

- Read `conversations.md` first to avoid duplicates
- Timestamp in ISO 8601 format (e.g., `2026-06-24T10:30:00-07:00`)
- Concise but complete — capture substance, not verbosity
- NEVER skip this step

## PHASE-BY-PHASE DEVELOPMENT

Build the project phase by phase. For each phase:
1. Create a phase-specific spec file at `spec/<phase-number>-<name>.md` (e.g., `001-ReAct-MVP.md`)
2. Plan and scope the phase with the user before coding
3. Implement only what's in the current phase scope — do not jump ahead
4. Mark the phase done before moving to the next
