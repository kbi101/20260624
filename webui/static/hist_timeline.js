/* ── HIST Timeline + Graph Renderer ─────────────────────────────────────────── */

let G = { events: [], persons: [], edges: [] };
let selectedNode = null;
let highlightNode = null;
let hoveredPerson = null;
let showPersons = true;
let showEvents = true;
let timelineZoom = 1;
let timelineOffsetX = 0;
let viewMode = "timeline";  // "timeline" or "graph"

// Graph view state
let graphNodes = [];  // Computed positions for force simulation
let simulating = false;
let simFrameCount = 0;  // Frames run this cycle (cap to auto-stop)
const MAX_SIM_FRAMES = 500;
let stableFrames = 0;   // Consecutive frames where max velocity < 0.5
let draggingGraphNode = null;

function setViewMode(mode) {
  if (mode === viewMode) return;
  viewMode = mode;
  document.getElementById("btnTimeline").classList.toggle("on", mode === "timeline");
  document.getElementById("btnGraph").classList.toggle("on", mode === "graph");
  if (mode === "graph" && !graphNodes.length) {
    initGraphPositions();
    simulating = true;
    simFrameCount = 0;
    runGraphSimulation();
  } else {
    simulating = false;
  }
  renderTimeline();
}

const canvas = document.getElementById("timeline");
const ctx = canvas.getContext("2d");

/* ── Load data & render ───────────────────────────────────────────── */

let currentGraphQuery = null;

async function loadGraph(query, hops, limit) {
  try {
    const params = new URLSearchParams();
    if (query) { params.set("query", query); currentGraphQuery = query; }
    if (hops) params.set("hops", hops);
    if (limit) params.set("limit", limit);
    const url = `/api/hist/graph-data${params.toString() ? '?' + params.toString() : ''}`;
    const r = await fetch(url);
    const d = await r.json();
    G.events = d.events || [];
    G.persons = d.persons || [];
    G.edges = d.edges || [];

    // Reset graph view state on reload
    graphNodes = [];
    simulating = false;

    updateStatsBadge();
    renderTimeline();
    buildPersonChips();
  } catch (e) {
    console.error("Failed to load graph:", e);
  }
}

async function searchGraphSub() {
  const q = document.getElementById("graphSearchInput").value.trim();
  if (!q) return;
  graphNodes = [];
  simulating = false;
  await loadGraph(q, 1, 80);
}

async function expandNodeNeighbours(targetId) {
  try {
    const r = await fetch(`/api/hist/expand-node/${encodeURIComponent(targetId)}/?hops=1`);
    const data = await r.json();
    if (!data.neighbours?.length) return;

    const existingIds = new Set([
      ...G.events.map(e => e.node_id),
      ...G.persons.map(p => p.node_id),
    ]);

    // Merge neighbours (skip already-present nodes)
    data.neighbours.forEach(nb => {
      if (existingIds.has(nb.node_id)) return;
      existingIds.add(nb.node_id);

      if (nb.label === "Event") {
        G.events.push({ node_id: nb.node_id, name: nb.name || nb.node_id, date: "", year: null });
      } else {
        G.persons.push({ node_id: nb.node_id, name: nb.name || nb.node_id });
      }
    });

    // Merge new edges (skip duplicates)
    const existingEdges = new Set(G.edges.map(e => `${e.src}||${e.rel}||${e.tgt}`));
    data.edges.forEach(ed => {
      const key = `${ed.src}||${ed.rel}||${ed.tgt}`;
      if (!existingEdges.has(key)) {
        G.edges.push({ src: ed.src, rel: ed.rel, tgt: ed.tgt });
        existingEdges.add(key);
      }
    });

    // Rebuild graph view, re-simulate from scratch
    stableFrames = 0;
    initGraphPositions();
    simulating = true;
    runGraphSimulation();

    updateStatsBadge();
    buildPersonChips();
  } catch (e) {
    console.error("Expand failed:", e);
  }
}

async function loadNodeDetail(id) {
  try {
    const r = await fetch("/api/hist/node-details/" + id);
    const d = await r.json();
    selectedNode = id;
    renderNodeCard(d);
  } catch (e) { console.error(e); }
}

async function doIngest() {
  const topic = document.getElementById("seedInput").value.trim();
  if (!topic) return;
  try {
    const r = await fetch("/api/hist/ingest", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({topic}) });
    const d = await r.json();
    console.log("Ingested:", d);
    loadGraph(currentGraphQuery);
  } catch (e) { console.error("Ingest failed:", e); }
}

async function doIngestAll() {
  try {
    const r = await fetch("/api/hist/ingest-queue", { method: "POST" });
    const d = await r.json();
    console.log("Queue done:", d);
    loadGraph(currentGraphQuery);
  } catch (e) { console.error(e); }
}

async function doAsk() {
  const q = document.getElementById("askInput").value.trim();
  if (!q) return;
  const area = document.getElementById("answerArea");
  area.innerHTML = '<p style="color:var(--text-muted)">Thinking…</p>';
  try {
    const r = await fetch("/api/hist/ask", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({question: q}) });
    const d = await r.json();
    renderAnswer(d);
  } catch (e) { area.innerHTML = '<p style="color:var(--danger)">Request failed.</p>'; }
}

/* ── Stats badge in header ─────────────────────────────────────── */

function updateStatsBadge() {
  e = G.events.length; p = G.persons.length; eg = G.edges.length;
  document.getElementById("statsBadge").textContent = `${e} events · ${p} persons · ${eg} edges`;
  document.getElementById("askStats").textContent = `zoom ${(timelineZoom * 100).toFixed(0)}%`;
}

/* ── Person chips in grid below header ─────────────────────────── */

function buildPersonChips() {
  const el = document.getElementById("personChips");
  el.innerHTML = "";
  G.persons.forEach(p => {
    const chip = document.createElement("span");
    chip.className = "person-chip";
    chip.textContent = p.name;
    chip.onclick = () => { loadNodeDetail(p.node_id); };
    chip.onmouseenter = () => { hoveredPerson = p.node_id; renderTimeline(); };
    chip.onmouseleave = () => { hoveredPerson = null; renderTimeline(); };
    el.appendChild(chip);
  });
}

/* ── Node detail card (left sidebar) ─────────────────────────── */

function renderNodeCard(d) {
  const area = document.getElementById("nodeDetailArea");
  if (!d || d.error) { area.innerHTML = '<p class="empty-msg">Node not found.</p>'; return; }

  let propsHtml = "";
  const pk = Object.entries(d.props || {});
  if (pk.length) {
    propsHtml = "<pre>" + JSON.stringify(pk.reduce((a, [k,v]) => ({...a,[k]:v}), {}), null, 2) + "</pre>";
  }

  let connHtml = "";
  if (d.connections && d.connections.length) {
    connHtml = d.connections.map(c => `
      <div class="conn-row">
        <span class="conn-node" onclick="loadNodeDetail('${c.src}')">${c.src}</span>
        <span class="conn-label">→ ${c.rel} →</span>
        <span class="conn-node" onclick="loadNodeDetail('${c.tgt}')">${c.tgt}</span>
      </div>`).join("");
  }

  area.innerHTML = `
    <div class="node-card">
      <h4>${d.name || d.node_id}</h4>
      ${propsHtml}
      <div style="margin-top:10px;">
        <strong style="font-size:.78rem;color:var(--text-secondary)">Connections (${(d.connections||[]).length}):</strong>
        ${connHtml || '<span style="color:var(--text-muted);font-size:.75rem">none</span>'}
      </div>
    </div>`;
}

/* ── Answer panel (right sidebar) ────────────────────────────── */

function renderAnswer(d) {
  const area = document.getElementById("answerArea");
  let evHtml = "";
  if (d.evidence && d.evidence.length) {
    evHtml = `<div class="evidence-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block';">Show evidence (${d.evidence.length} entries)</div>
      <div class="evidence-list">${d.evidence.map(e => {
        let parts = [];
        if (e.name) parts.push(`<strong>${e.name}</strong>`);
        if (e.label) parts.push(`(${e.label})`);
        if (e.date) parts.push(`[${e.date}]`);
        if (e.src && e.tgt) parts.push(`${e.src} --&gt; ${e.tgt}`);
        return parts.length ? `<div>• ${parts.join(" ")}</div>` : "";
      }).join("")}</div>`;
  }

  area.innerHTML = `
    <h4>Answer</h4>
    <p>${escapeHtml(d.answer)}</p>
    <span style="font-size:.72rem;color:var(--text-muted)">${d.nodes_used || 0} nodes · ${d.edges_used || 0} edges used</span>
    ${evHtml}`;
}

function escapeHtml(s) {
  const m = document.createElement("span");
  m.textContent = s;
  return m.innerHTML;
}

/* ── Timeline Canvas Renderer ─────────────────────────────────── */

const TIMELINE_Y_RATIO = 0.38;

function resizeCanvas() {
  const panel = document.getElementById("centerPanel");
  canvas.width = panel.clientWidth * devicePixelRatio;
  canvas.height = (panel.clientHeight - 128) * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
}

function renderTimeline() {
  resizeCanvas();
  
  // Switch between timeline and graph views
  if (viewMode === "graph") {
    if (!graphNodes.length) {
      initGraphPositions();
      simulating = true;
      runGraphSimulation();
      return;
    }
    renderGraphView();
    return;
  }
  
  // Timeline view
  const W = canvas.width / devicePixelRatio;
  const H = canvas.height / devicePixelRatio;

  ctx.clearRect(0, 0, W, H);

  if (!G.events.length) return;

  const years = G.events.map(e => e.year).filter(y => y != null && y > 1400);
  if (!years.length) {
    ctx.fillStyle = "#5a6170";
    ctx.font = "13px Inter, sans-serif";
    ctx.fillText("No event dates available for timeline.", 20, 40);
    return;
  }

  const minY = Math.min(...years) - 10;
  const maxY = Math.max(...years) + 10;
  const span = (maxY - minY) || 1;

  const padX = 50 * timelineZoom;
  const usableW = W - padX * 2;
  const tlY = H * TIMELINE_Y_RATIO;

  // Apply pan offset
  ctx.save();
  ctx.translate(timelineOffsetX, 0);

  // Draw grid lines at decade boundaries
  const decadeStart = Math.floor(minY / 10) * 10;
  for (let y = decadeStart; y <= maxY; y += 10) {
    const x = padX + ((y - minY) / span) * usableW * timelineZoom;
    if (x < 0 || x > W + padX) continue;
    ctx.strokeStyle = "rgba(255,255,255,.06)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, tlY - 50);
    ctx.lineTo(x, tlY + 80);
    ctx.stroke();

    if (y % 20 === 0) {
      ctx.fillStyle = "rgba(255,255,255,.3)";
      ctx.font = "11px Inter";
      ctx.textAlign = "center";
      ctx.fillText(y, x, tlY + 95);
    }
  }

  // Draw timeline axis line
  const startX = padX - 20 * timelineZoom;
  const endX = padX + usableW * timelineZoom + 20 * timelineZoom;

  ctx.strokeStyle = "rgba(108,92,231,.5)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(startX, tlY);
  ctx.lineTo(endX, tlY);
  ctx.stroke();

  // Draw events as pill badges on/near timeline
  const eventPositions = [];
  let eventRow = 0;

  if (showEvents) {
    G.events.forEach(e => {
      if (!e.year || e.year < minY || e.year > maxY) return;
      const x = padX + ((e.year - minY) / span) * usableW * timelineZoom;
      if (x < padX - 30 || x > padX + usableW * timelineZoom + 30) return;

      eventPositions.push({ type: "event", x, y: tlY });

      const isSel = selectedNode === e.node_id;
      const isHighlight = highlightNode === e.node_id;
      const opacity = isSel || isHighlight ? 1 : (hoveredPerson ? .35 : .85);

      ctx.globalAlpha = opacity;
      const name = e.name || e.node_id;
      ctx.font = "bold 11px Inter";
      const tw = ctx.measureText(name).width + 20;
      const pillH = 26;

      let pillY = tlY - pillH - 6;
      if (pillY < 5) pillY = tlY + 8;

      // Pill background
      ctx.fillStyle = isSel ? "#c8b6ff" : (isHighlight ? "rgba(108,92,231,.3)" : "rgba(108,92,231,.15)");
      fillRoundRect(ctx, x - tw / 2, pillY - pillH / 2, tw, pillH, pillH / 2);
      ctx.fill();

      if (isSel || isHighlight) {
        ctx.strokeStyle = "#6c5ce7";
        ctx.lineWidth = 1.5;
        fillRoundRect(ctx, x - tw / 2, pillY - pillH / 2, tw, pillH, pillH / 2);
        ctx.stroke();
      }

      // Text
      ctx.fillStyle = isSel ? "#000" : (isHighlight ? "#c8b6ff" : "#90a4ae");
      ctx.font = "bold 10px Inter";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const maxChars = Math.floor((tw - 16) / 7);
      const clamped = name.length > maxChars ? name.slice(0, maxChars - 2) + "…" : name;
      ctx.fillText(clamped, x, pillY);

      // Dot on axis
      ctx.fillStyle = isSel ? "#fff" : "#6c5ce7";
      ctx.beginPath();
      ctx.arc(x, tlY, 3.5, 0, Math.PI * 2);
      ctx.fill();

      eventRow++;
    });

    ctx.globalAlpha = 1;
  }

  // Highlight edges connected to hovered/selected person
  if (hoveredPerson || selectedNode) {
    const targetId = hoveredPerson || selectedNode;
    G.edges.forEach(ed => {
      if (ed.src !== targetId && ed.tgt !== targetId) return;
      const srcXy = eventPositions.find(ep => ep.node_id === ed.src);
      const tgtXy = eventPositions.find(ee => ee.node_id === ed.tgt);
      // edges are drawn between people and events if both on screen
    });

    ctx.strokeStyle = "rgba(253,121,168,.3)";
    ctx.lineWidth = 1;
    G.edges.forEach(ed => {
      if (ed.src !== targetId && ed.tgt !== targetId) return;
      const otherId = ed.src === targetId ? ed.tgt : ed.src;
      const ep = eventPositions.find(e => e.node_id === otherId);
      if (!ep) return;
      ctx.beginPath();
      ctx.moveTo(ep.x, tlY);
      ctx.lineTo(ep.x, tlY + 60);
      ctx.stroke();
    });
  }

  // Draw legend bottom-right
  ctx.globalAlpha = .5;
  ctx.font = "10px Inter";
  ctx.fillStyle = "#6c5ce7";
  ctx.textAlign = "right";
  ctx.fillText("● Events", W - padX / 2, H - 12);
  if (hoveredPerson) {
    ctx.fillStyle = "#fd79a8";
    ctx.fillText("— Connected edges", W - padX / 2, H - 26);
  }

  ctx.restore();
}

/* ── Graph View Renderer (force-directed) ───────────────────────── */

function initGraphPositions() {
  graphNodes = [];
  const W = canvas.width / devicePixelRatio;
  const H = canvas.height / devicePixelRatio;
  const cx = W / 2;
  const cy = H / 2;
  const ringRadius = Math.min(W, H) * 0.35;

  const allItems = [
    ...G.events.map(e => ({ node_id: e.node_id, name: e.name || e.node_id, type: "event", year: e.year || 0, mass: 2 })),
    ...G.persons.map(p => ({ node_id: p.node_id, name: p.name || p.node_id, type: "person", mass: 1.5 }))
  ];

  const cache = loadNodePositions();

  allItems.forEach((item, i) => {
    const angle = (2 * Math.PI * i) / allItems.length;
    const restored = cache ? cache[item.node_id] : null;
    graphNodes.push({
      ...item,
      x: restored ? restored.x : cx + ringRadius * Math.cos(angle),
      y: restored ? restored.y : cy + ringRadius * Math.sin(angle),
      vx: 0, vy: 0
    });
  });
}

function simulateGraphStep() {
  const W = canvas.width / devicePixelRatio;
  const H = canvas.height / devicePixelRatio;
  const center = { x: W / 2, y: H / 2 };

  const repelStrength = 1200;
  const attractStrength = 0.06;
  const damping = 0.85;
  const maxDisplacement = 50;
  const minDist = 70;

  const nodeIndex = new Map(graphNodes.map(n => [n.node_id, n]));

  // Apply repulsion between all node pairs (with minimum distance floor)
  for (let i = 0; i < graphNodes.length; i++) {
    for (let j = i + 1; j < graphNodes.length; j++) {
      const a = graphNodes[i];
      const b = graphNodes[j];
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;

      // Stronger repulsion below minDist to prevent overlap
      if (dist < minDist) {
        const push = (minDist - dist) * 0.5;
        a.vx += (dx / dist) * push;
        a.vy += (dy / dist) * push;
        b.vx -= (dx / dist) * push;
        b.vy -= (dy / dist) * push;
      } else {
        const force = repelStrength / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx * b.mass;
        a.vy -= fy * b.mass;
        b.vx += fx * a.mass;
        b.vy += fy * a.mass;
      }
    }
  }

  // Apply attraction along edges
  G.edges.forEach(edge => {
    const a = nodeIndex.get(edge.src);
    const b = nodeIndex.get(edge.tgt);
    if (!a || !b) return;

    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist > 0) {
      const force = (dist - 180) * attractStrength;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }
  });

  // Center gravitation + integrate
  graphNodes.forEach(node => {
    const dx = center.x - node.x;
    const dy = center.y - node.y;
    node.vx += dx * 0.1;
    node.vy += dy * 0.1;

    node.vx *= damping;
    node.vy *= damping;

    const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
    if (speed > 0) {
      const cap = Math.min(speed, maxDisplacement);
      node.x += (node.vx / speed) * cap;
      node.y += (node.vy / speed) * cap;
    }

    node.x = Math.max(20, Math.min(W - 20, node.x));
    node.y = Math.max(20, Math.min(H - 20, node.y));
  });
}

function runGraphSimulation() {
  // Pre-compute all steps synchronously so the user never sees nodes jiggle
  for (let i = 0; i < MAX_SIM_FRAMES; i++) {
    simulateGraphStep();

    let maxSpeed = 0;
    graphNodes.forEach(n => {
      const spd = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (spd > maxSpeed) maxSpeed = spd;
    });

    if (maxSpeed < 0.5) {
      stableFrames++;
      if (stableFrames >= 50) break;
    } else {
      stableFrames = 0;
    }
  }
  simulating = false;
  renderGraphView();
}

function renderGraphView() {
  const W = canvas.width / devicePixelRatio;
  const H = canvas.height / devicePixelRatio;
  
  ctx.clearRect(0, 0, W, H);

  // Pre-compute neighbor set for selected/hovered node
  const highlightIds = new Set();
  if (selectedNode || highlightNode) {
    const targetId = selectedNode || highlightNode;
    G.edges.forEach(edge => {
      if (edge.src === targetId) highlightIds.add(edge.tgt);
      if (edge.tgt === targetId) highlightIds.add(edge.src);
    });
  }

  // Draw edges with type labels
  G.edges.forEach(edge => {
    const src = graphNodes.find(n => n.node_id === edge.src);
    const tgt = graphNodes.find(n => n.node_id === edge.tgt);
    if (!src || !tgt) return;
    const isHighlighted = (selectedNode && (edge.src === selectedNode || edge.tgt === selectedNode)) ||
                          (highlightNode && (edge.src === highlightNode || edge.tgt === highlightNode));
    ctx.strokeStyle = isHighlighted ? "rgba(253,121,168,.6)" : "rgba(255,255,255,.15)";
    ctx.lineWidth = isHighlighted ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.stroke();

    // Edge type label at midpoint
    if (edge.type) {
      const mx2 = (src.x + tgt.x) / 2;
      const my2 = (src.y + tgt.y) / 2;
      ctx.font = "9px Inter";
      ctx.fillStyle = isHighlighted ? "#fd79a8" : "rgba(255,255,255,.35)";
      ctx.textAlign = "center";
      const bg2 = mx2 - ctx.measureText(edge.type).width / 2 - 4;
      ctx.fillText(edge.type, mx2, my2);
    }
  });

  // Draw nodes — circles with labels below for clarity
  graphNodes.forEach(node => {
    const isSelected = selectedNode === node.node_id;
    const isHovered = highlightNode === node.node_id;
    const isNeighbor = highlightIds.has(node.node_id);
    const alpha = (isSelected || isHovered || isNeighbor) ? 1 : 0.55;

    ctx.globalAlpha = alpha;

    // Node body
    const radius = isSelected ? 28 : (isHovered || isNeighbor ? 24 : 20);
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = node.type === "event" ? "#6c5ce7" : "#fd79a8";
    ctx.fill();

    if (isSelected || isHovered) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Label below circle
    ctx.globalAlpha = alpha > 0.7 ? 1 : 0.6;
    ctx.fillStyle = isSelected ? "#fff" : (isHovered || isNeighbor ? "#dfe6e9" : "rgba(255,255,255,.65)");
    ctx.font = `${isSelected || isHovered ? 'bold ' : ''}${10}px Inter`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    const maxChars = 24;
    const clamped = node.name.length > maxChars ? node.name.slice(0, maxChars - 1) + "…" : node.name;
    ctx.fillText(clamped, node.x, node.y + radius + 6);
  });

  ctx.globalAlpha = 1;
  ctx.textBaseline = "alphabetic";
  
  ctx.globalAlpha = 1;
  
  // Legend
  ctx.font = "11px Inter";
  ctx.textAlign = "right";
  ctx.fillStyle = "rgba(108,92,231,0.8)";
  ctx.fillText("● Events", W - 20, H - 12);
  ctx.fillStyle = "rgba(253,121,168,0.8)";
  ctx.fillText("● Persons", W - 20, H - 28);
  
  // Zoom controls
  const zoomStr = document.getElementById("askStats").textContent;
  if (!zoomStr.includes("zoom")) {
    ctx.font = "10px Inter";
    ctx.fillStyle = "rgba(255,255,255,0.5)";
    ctx.fillText("Scroll to zoom • Drag to pan", W - 20, H - 45);
  }
}

function fillRoundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.lineTo(x + w - r, y);
  c.quadraticCurveTo(x + w, y, x + w, y + r);
  c.lineTo(x + w, y + h - r);
  c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  c.lineTo(x + r, y + h);
  c.quadraticCurveTo(x, y + h, x, y + h - r);
  c.lineTo(x, y + r);
  c.quadraticCurveTo(x, y, x + r, y);
  c.closePath();
}

 /* ── Mouse interaction ─────────────────────────────────────────── */

let isPanning = false;
let dragStartPos = null;
let didDrag = false;

// ── localStorage persistence for node positions ────────────────────
function saveNodePositions() {
  const map = {};
  graphNodes.forEach(n => { map[n.node_id] = { x: n.x, y: n.y }; });
  try { localStorage.setItem("hist_graph_positions", JSON.stringify(map)); } catch(_e) {}
}

function loadNodePositions() {
  try {
    const raw = localStorage.getItem("hist_graph_positions");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch(_e) {}
  return null;
}

canvas.addEventListener("mousedown", e => {
  if (e.button !== 0) return;
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  if (viewMode === "graph") {
    for (const nd of graphNodes) {
      const dx = mx - nd.x;
      const dy = my - nd.y;
      if (Math.sqrt(dx * dx + dy * dy) < 45) {
        dragStartPos = { x: mx, y: my };
        draggingGraphNode = nd;
        didDrag = false;
        return;
      }
    }
    isPanning = true;
    dragStartPos = { x: mx, y: my };
    didDrag = false;
    return;
  }

  // Timeline mode — no change on mousedown in timeline mode
});

canvas.addEventListener("mouseup", e => {
  if (draggingGraphNode) {
    // Only treat as a click if mouse barely moved
    if (!didDrag && dragStartPos) {
      const dx = e.clientX - dragStartPos.x;
      const dy = e.clientY - dragStartPos.y;
      if (Math.sqrt(dx * dx + dy * dy) < 6) {
        loadNodeDetail(draggingGraphNode.node_id);
      }
    } else if (didDrag) {
      saveNodePositions();
    }
    draggingGraphNode = null;
    dragStartPos = null;
    didDrag = false;
    return;
  }
  isPanning = false;
});

canvas.addEventListener("mousemove", e => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  if (viewMode === "graph") {
    if (draggingGraphNode) {
      if (dragStartPos) {
        const dx = mx - dragStartPos.x;
        const dy = my - dragStartPos.y;
        if (Math.sqrt(dx * dx + dy * dy) > 4) didDrag = true;
      }
      draggingGraphNode.x = mx;
      draggingGraphNode.y = my;
      renderGraphView();
      return;
    }

    // Hover highlight
    let hit = null;
    for (const nd of graphNodes) {
      const dx = mx - nd.x;
      const dy = my - nd.y;
      if (Math.sqrt(dx * dx + dy * dy) < 35) { hit = nd; break; }
    }
    highlightNode = hit ? hit.node_id : null;

    // Pan background
    if (isPanning) {
      graphNodes.forEach(n => {
        n.x += e.movementX;
        n.y += e.movementY;
      });
      renderGraphView();
      return;
    }

    renderGraphView();
    return;
  }

  // Timeline mode — pan
  if (isPanning) {
    timelineOffsetX += e.movementX;
    renderTimeline();
    return;
  }

  // Timeline mode — hover
  const years = G.events.map(ev => ev.year).filter(y => y != null && y > 1400);
  if (!years.length) return;

  const minY = Math.min(...years) - 10;
  const maxY = Math.max(...years) + 10;
  const span = (maxY - minY) || 1;
  const padX = 50 * timelineZoom;
  const usableW = rect.width - padX * 2;
  const tlY = rect.height * TIMELINE_Y_RATIO;

  let hitEv = null;
  G.events.forEach(ev => {
    if (!ev.year || ev.year < minY || ev.year > maxY) return;
    const x = (padX + ((ev.year - minY) / span) * usableW * timelineZoom) - timelineOffsetX;
    if (Math.abs(mx - x) < 30 && Math.abs(my - tlY) < 40) hitEv = ev;
  });

  highlightNode = hitEv ? hitEv.node_id : null;
  renderTimeline();
});

canvas.addEventListener("click", e => {
  // Graph clicks now handled in mouseup (distinguishes drag from tap).
  if (viewMode === "graph") return;

  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  const years = G.events.map(ev => ev.year).filter(y => y != null && y > 1400);
  if (!years.length) return;

  const minY = Math.min(...years) - 10;
  const maxY = Math.max(...years) + 10;
  const span = (maxY - minY) || 1;
  const padX = 50 * timelineZoom;
  const usableW = rect.width - padX * 2;
  const tlY = rect.height * TIMELINE_Y_RATIO;

  G.events.forEach(ev => {
    if (!ev.year) return;
    const x = (padX + ((ev.year - minY) / span) * usableW * timelineZoom) - timelineOffsetX;
    if (Math.abs(mx - x) < 30 && Math.abs(my - tlY) < 40) {
      loadNodeDetail(ev.node_id);
    }
  });
});

canvas.addEventListener("dblclick", e => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  if (viewMode === "graph") {
    for (const node of graphNodes) {
      const dx = mx - node.x;
      const dy = my - node.y;
      if (Math.sqrt(dx * dx + dy * dy) < 18) {
        expandNodeNeighbours(node.node_id);
        return;
      }
    }
  }
});

canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  timelineZoom = Math.max(0.5, Math.min(4, timelineZoom * delta));
  renderTimeline();
  document.getElementById("askStats").textContent = `zoom ${(timelineZoom * 100).toFixed(0)}%`;
}, { passive: false });

/* ── Init ─────────────────────────────────────────────────────────── */

loadGraph();
window.addEventListener("resize", () => { resizeCanvas(); renderTimeline(); });
