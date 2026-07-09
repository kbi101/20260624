/* ── HIST Timeline Renderer ─────────────────────────────────────────── */

let G = { events: [], persons: [], edges: [] };
let selectedNode = null;
let highlightNode = null;
let hoveredPerson = null;
let showPersons = true;
let showEvents = true;
let timelineZoom = 1;
let timelineOffsetX = 0;

const canvas = document.getElementById("timeline");
const ctx = canvas.getContext("2d");

/* ── Load data & render ───────────────────────────────────────────── */

async function loadGraph() {
  try {
    const r = await fetch("/api/hist/graph-data");
    const d = await r.json();
    G.events = d.events || [];
    G.persons = d.persons || [];
    G.edges = d.edges || [];
    updateStatsBadge();
    renderTimeline();
    buildPersonChips();
  } catch (e) {
    console.error("Failed to load graph:", e);
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
    loadGraph();
  } catch (e) { console.error("Ingest failed:", e); }
}

async function doIngestAll() {
  try {
    const r = await fetch("/api/hist/ingest-queue", { method: "POST" });
    const d = await r.json();
    console.log("Queue done:", d);
    loadGraph();
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

canvas.addEventListener("mousemove", e => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  // Check if clicking on an event pill (approximate hit test)
  const years = G.events.map(ev => ev.year).filter(y => y != null && y > 1400);
  if (!years.length) return;

  const minY = Math.min(...years) - 10;
  const maxY = Math.max(...years) + 10;
  const span = (maxY - minY) || 1;
  const padX = 50 * timelineZoom;
  const usableW = rect.width - padX * 2;
  const tlY = rect.height * TIMELINE_Y_RATIO;

  let hit = null;
  G.events.forEach(ev => {
    if (!ev.year || ev.year < minY || ev.year > maxY) return;
    const x = (padX + ((ev.year - minY) / span) * usableW * timelineZoom) - timelineOffsetX;
    if (Math.abs(mx - x) < 30 && Math.abs(my - tlY) < 40) hit = ev;
  });

  highlightNode = hit ? hit.node_id : null;
  renderTimeline();
});

canvas.addEventListener("click", e => {
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

canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  timelineZoom = Math.max(0.5, Math.min(4, timelineZoom * delta));
  renderTimeline();
  document.getElementById("askStats").textContent = `zoom ${(timelineZoom * 100).toFixed(0)}%`;
}, { passive: false });

let isDragging = false;
canvas.addEventListener("mousedown", e => { if (e.button === 0) isDragging = true; });
canvas.addEventListener("mouseup", () => { isDragging = false; });
canvas.addEventListener("mousemove", e => {
  if (!isDragging) return;
  timelineOffsetX += e.movementX;
  renderTimeline();
});

/* ── Init ─────────────────────────────────────────────────────────── */

loadGraph();
window.addEventListener("resize", () => { resizeCanvas(); renderTimeline(); });
