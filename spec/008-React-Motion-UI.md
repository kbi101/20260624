# Phase 008 — React Motion UI Upgrade

## Overview

Morphos currently uses server-rendered HTML templates (`index.html`, `dashboard.html`, `hist_index.html`) with vanilla JS scripts (`dash.js`, `hist_timeline.js`). While functional, it lacks modern motion UI features such as physics-based layout transitions, fluid spring animations, micro-interactions, responsive glassmorphism component architecture, and high-performance interactive graph visualizers.

This phase upgrades the entire WebUI into a unified, ultra-modern **React Motion UI** SPA built with **React 19**, **Vite**, **Framer Motion**, **Tailwind CSS**, **Lucide Icons**, and **D3 / Canvas** graph visualizers.

---

## Design Principles & Aesthetics

1. **Fluid Physics & Motion**: Powered by `framer-motion`, every state change (topic generation, card expansion, tab switching, history drawer opening) uses spring physics, layout animations, and staggered entrance effects.
2. **Cyberpunk Dark Glassmorphism**: Neon gradients (purple `#6c5ce7`, cyan `#00cec9`, pink `#fd79a8`), translucent frosted glass cards (`backdrop-filter: blur(18px)`), subtle glowing particles, and crisp monospace details (`JetBrains Mono`).
3. **Unified Single-Page Experience**: Smooth top-level tab navigation between the **Cognitive Dashboard (UCT)** and the **HIST Knowledge Graph**.
4. **Interactive Graph & Timeline Engine**:
   - **Knowledge Graph**: Hybrid SVG/Canvas force-directed network rendered via `d3-force` with Framer Motion hover cards, node expansion, zoom/pan controls, and animated prerequisite particle pulses.
   - **HIST Timeline**: Scrubbable event timeline with person/event node chips and side Q&A drawer.
5. **Backwards Compatibility**: The FastAPI backend (`server.py`, `hist_app.py`) continues serving clean JSON APIs without breaking existing data contracts or CLI integrations.

---

## Technical Stack

- **Frontend Framework**: React 19 + Vite + TypeScript
- **Styling**: Tailwind CSS + Custom Glassmorphism Theme Tokens
- **Animations & Micro-interactions**: `framer-motion`
- **Icons**: `lucide-react`
- **Visualizers**: `d3-force` + HTML5 Canvas / SVG
- **Data Layer**: TanStack React Query + Axios / Fetch

---

## Implementation Plan & Steps

1. Create `spec/008-React-Motion-UI.md` (this file).
2. Initialize `webui/frontend` package with Vite, React 19, TypeScript, Framer Motion, Lucide icons, D3-force, and Tailwind CSS.
3. Build common motion components (Header, OrbBackground, Glass Cards, History Drawer).
4. Build Cognitive Dashboard components (Hero search, Dimension bars, Concept cards, Sequence flow, Causal loop diagram, Matrix grid, Interactive Force Graph).
5. Build HIST Knowledge Graph components (Controls bar, Timeline canvas, Entity chips, Q&A drawer with evidence viewer).
6. Update FastAPI server `webui/server.py` to serve JSON endpoints and host `webui/frontend/dist` as the primary static bundle.
7. Build production bundle (`npm run build`) and verify end-to-end functionality.
