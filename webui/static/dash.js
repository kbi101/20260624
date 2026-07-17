// ─── morphos/webui/static/dash.js ─────────────────────────────────


// Landing page helpers
function setTopic(text) {
  const inp = document.getElementById('topicInput');
  if (inp) { inp.value = text; inp.focus(); }
}

async function loadHistory() {
  const list = document.getElementById('historyList');
  if (!list) return;
  try {
    const res = await fetch('/api/history');
    const entries = await res.json();
    if (!entries.length) {
      list.innerHTML = '<p style="color:var(--text-muted);font-size:.82rem">No topics yet. Generate one to see it here.</p>';
      return;
    }
    list.innerHTML = '';
    entries.slice(0, 10).forEach(e => {
      const a = document.createElement('a');
      a.className = 'history-item';
      const ts = e.timestamp ? new Date(e.timestamp) : null;
      const dateStr = ts ? ts.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
      a.innerHTML = `<span class="history-topic">${esc(e.topic)}</span><span class="history-time">${dateStr}</span>`;
      a.href = `/api/data?topic=${encodeURIComponent(e.topic)}`;
      list.appendChild(a);
    });
  } catch(err) { console.warn('History load failed', err); }
}


// Landing page setup
document.addEventListener('DOMContentLoaded', () => {
  loadHistory();

  if (typeof DATA !== 'undefined') return;
});

const DIM_COLORS = {
  structural: '#6c5ce7',
  sequential: '#00cec9',
  causal: '#fd79a8',
  comparative: '#ffeaa7',
  spatial: '#e17055',
  abstract: '#a29bfe',
};


/* ─── Dashboard render entry point ────────── */

document.addEventListener('DOMContentLoaded', () => {
  if (typeof DATA !== 'undefined') {
    document.getElementById('loading')?.remove();

    const d = DATA;
    renderHeader(d);
    renderDimensions(d.dimensions);
    renderConcepts(d.concepts, d.scaled_concepts);
    renderSequences(d.sequence_blocks);
    renderLoops(d.causal_loops);
    renderMatrices(d.matrices);
    renderScaleLayers(d.scaled_concepts);
    renderCompressions(d.compressions);
    renderGraph(d.graph);
    renderReferences(REFS || []);
  }
});


/* ─── Header ─────────────────────────────── */

function renderHeader(data) {
  const el = document.getElementById('essenceLine');
  if (!el) return;
  let essence = '';
  if (data.compressions?.[0]?.level_0_essence) essence = data.compressions[0].level_0_essence;
  else if (data.concepts?.[0]) essence = `${data.concepts[0].name}: ${data.concepts[0].definition}`;
  el.textContent = essence;

  const h2 = document.querySelector('.topic-name');
  if (h2) h2.textContent = data.topic;
  document.title = `${data.topic} — Cognitive Dashboard`;
}


/* ─── Dimensions ─────────────────────────── */

function renderDimensions(dims) {
  const container = document.getElementById('dimSection');
  if (!container || !dims) return;

  const entries = Object.entries(dims).filter(([k]) => typeof dims[k] === 'number');

  entries.forEach(([name, weight]) => {
    const row = document.createElement('div');
    row.className = 'dim-row';
    const pct = Math.round(weight * 100);
    const col = DIM_COLORS[name] || '#888';
    row.innerHTML = `
      <div class="dim-label">
        <span style="color:${col};font-weight:600;text-transform:capitalize">${name}</span>
        <span>${weight.toFixed(2)}</span>
      </div>
      <div class="dim-track"><div class="dim-fill" style="background:${col}" data-width="${pct}"></div></div>`;
    container.appendChild(row);
  });

  // Animate after paint
  requestAnimationFrame(() => {
    document.querySelectorAll('.dim-fill').forEach(el => {
      el.style.width = (el.dataset.width || 0) + '%';
    });
  });
}


/* ─── Concept cards ─────────────────────── */

function renderConcepts(concepts, scaled) {
  const grid = document.getElementById('conceptGrid');
  if (!grid || !concepts?.length) return;

  const palette = ['#6c5ce7','#00cec9','#fd79a8','#ffeaa7','#e17055','#a29bfe','#fab1a0','#dfe6e9'];
  
  concepts.forEach((c, i) => {
    const card = document.createElement('div');
    card.className = 'c-card';
    card.style.setProperty('--card-accent', palette[i % palette.length]);

    let chips = '';
    (c.constraints||[]).forEach(x => chips += `<span class="constraint-chip">${esc(x)}</span>`);
    (c.failure_modes||[]).forEach(x => chips += `<span class="failure-chip">⚠ ${esc(x)}</span>`);

    card.innerHTML = `
      <div style="position:absolute;top:0;left:0;right:0;height:3px;background:${palette[i%palette.length]};border-radius:var(--radius-md) var(--radius-md) 0 0"></div>
      <div class="c-name">${esc(c.name)}</div>
      <div class="c-def">${esc(c.definition)}</div>
      ${c.why_it_exists ? `<div class="c-why">Why: ${esc(c.why_it_exists)}</div>` : ''}
      <div>${chips}</div>`;
    grid.appendChild(card);
  });
}


/* ─── Sequences ─────────────────────────── */

function renderSequences(seqs) {
  const area = document.getElementById('seqArea');
  if (!area || !seqs?.length) return;

  seqs.forEach(seq => {
    area.innerHTML += `<div class="section-title">Process: ${esc(seq.title)}</div>`;
    let html = '<div class="seq-card">\n';
    seq.steps.forEach((s, idx) => {
      html += `<div class="step-item">
        <div class="step-num">${idx+1}</div>
        <div class="step-body">
          <div class="step-label">${esc(s.label)}${s.prerequisites?.length ? ' <span style="color:var(--text-muted);font-size:.72rem">(needs: '+s.prerequisites.join(', ')+')</span>' : ''}</div>
          ${s.input ? `<div class="step-desc">Input: ${esc(s.input)}</div>` : ''}
          ${s.transformation ? `<div class="step-desc">→ ${esc(s.transformation)}</div>` : ''}
          ${s.validation ? `<div class="step-desc">✓ Check: ${esc(s.validation)}</div>` : ''}
          ${s.output ? `<div class="step-desc">Output: ${esc(s.output)}</div>` : ''}
          ${s.failure_condition ? `<div class="step-fail">⚠ ${esc(s.failure_condition)}</div>` : ''}
        </div>
      </div>\n`;
    });
    html += '</div>';
    area.innerHTML += html;
  });
}


/* ─── Causal Loops ──────────────────────── */

function renderLoops(loops) {
  const area = document.getElementById('loopArea');
  if (!area || !loops?.length) return;

  loops.forEach(loop => {
    const badge_cls = loop.loop_type === 'reinforcing' ? 'badge-reinforcing' : 'badge-balancing';
    let html = `<div class="section-title">Causal Loop: ${esc(loop.title)}</div><div class="loop-card">
      <span class="loop-type-badge ${badge_cls}">${loop.loop_type}</span>\n`;

    (loop.loops||[]).forEach(cycle => {
      html += `<div class="cycle-row">  Cycle: ${cycle.join(' → ')}</div>`;
    });
    (loop.links||[]).forEach(l => {
      const icon = l.effect?.includes('increas') ? '↑' : '↓';
      html += `<div class="cycle-row">${icon} ${esc(l['from'])} ──[${esc(l.effect)}]──> ${esc(l.to)}</div>`;
    });

    html += '</div>';
    area.innerHTML += html;
  });
}


/* ─── Matrices ───────────────────────────── */

function renderMatrices(matrices) {
  const area = document.getElementById('matrixArea');
  if (!area || !matrices?.length) return;

  matrices.forEach(mx => {
    let html = `<div class="section-title">Comparison: ${esc(mx.title)}</div><div class="table-wrap"><table>
      <thead><tr><th>Attribute</th>${mx.options.map(o=>`<th>${esc(o)}</th>`).join('')}</tr></thead><tbody>`;
    mx.attributes.forEach(a => {
      html += `<tr><td>${esc(a)}</td>`;
      mx.options.forEach(o => {
        const val = mx.cells[`${a}|${o}`] || '';
        html += `<td>${esc(val)}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table></div>`;
    area.innerHTML += html;
  });
}


/* ─── Scale Layers ──────────────────────── */

function renderScaleLayers(scaled) {
  const area = document.getElementById('scaleArea');
  if (!area || !scaled?.length) return;

  const order = ['physical','component','system','network','emergent'];
  let html = `<div class="section-title">Scale Layers</div><div class="glass-card" style="padding:20px;margin-bottom:36px">`;

  order.forEach(lvl => {
    const items = scaled.filter(s => s.scale === lvl);
    if (!items.length) return;
    html += `<div class="scale-layer"><span class="scale-tag" style="background:rgba(108,92,231,.15);color:var(--accent-1)">${lvl}</span>`;
    items.forEach(s => html += `<span style="font-size:.84rem;color:var(--text-secondary)"> ${esc(s.name)}</span>`);
    html += `</div>`;
  });

  html += `</div>`;
  area.innerHTML = html;
}


/* ─── Compressions (expert notes) ──────── */

function renderCompressions(comps) {
  const area = document.getElementById('compArea');
  if (!area || !comps?.length) return;

  let html = `<div class="section-title">Expert Notes</div>`;
  comps.forEach(c => {
    if (!c.level_3_expert) return;
    html += `<div class="glass-card" style="padding:20px;margin-bottom:14px">
      <div class="c-name">${esc(c.concept_name)}</div>
      <div style="color:var(--text-secondary);font-size:.84rem;line-height:1.6;white-space:pre-line">${esc(c.level_3_expert)}</div>
    </div>`;
  });
  area.innerHTML = html;
}


/* ─── References ────────────────────────── */

function renderReferences(refs) {
  const list = document.getElementById('refList');
  if (!list) return;
  if (!refs?.length) {
    list.innerHTML = '<li class="ref-item"><span style="color:var(--text-muted)">No web sources fetched. The dashboard was generated from model knowledge.</span></li>';
    return;
  }
  refs.forEach((r, i) => {
    const li = document.createElement('li');
    li.className = 'ref-item';
    li.innerHTML = `
      <span class="ref-num">${i+1}</span>
      <div class="ref-body">
        <span class="ref-title">${esc(r.title)}</span>
        <span class="ref-url"><a href="${esc(r.url)}" target="_blank">${esc(r.url)}</a></span>
      </div>`;
    list.appendChild(li);
  });
}


/* ─── Knowledge Graph (Canvas) ───────────── */

function renderGraph(graphData) {
  const canvas = document.getElementById('graphCanvas');
  if (!canvas || !graphData?.nodes?.length) return;

  const ctx = canvas.getContext('2d');
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight;
  canvas.width = w * devicePixelRatio;
  canvas.height = h * devicePixelRatio;
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  ctx.scale(devicePixelRatio, devicePixelRatio);

  const adj = graphData.adjacency || {};
  const nodeList = graphData.nodes;

  // Build edge list from adjacency
  const edges = [];
  const seen = new Set();  
  for (const [src, neighbors] of Object.entries(adj)) {
    for (const nb of neighbors) {
      const key = [src, nb.name].sort().join('||');
      if (!seen.has(key)) {
        seen.add(key);
        edges.push({ from: src, to: nb.name, type: nb.edge_type || 'prerequisite' });
      }
    }
  }

  // Assign nodes positions via hierarchical force-directed layout (mind-map style)
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) * 0.42;

  // Compute node degrees to find root/high-degree hubs
  const degree = {};
  nodeList.forEach(n => { degree[n] = 0; });
  edges.forEach(e => {
    if (degree[e.from] !== undefined) degree[e.from]++;
    if (degree[e.to] !== undefined) degree[e.to]++;
  });

  // Sort nodes by degree descending — hubs first for radial placement
  const sorted = [...nodeList].sort((a, b) => (degree[b]||0) - (degree[a]||0));

  // Identify connected components for grouping
  const visited = new Set();
  const components = [];
  nodeList.forEach(start => {
    if (visited.has(start)) return;
    const comp = [];
    const stack = [start];
    while (stack.length) {
      const cur = stack.pop();
      if (visited.has(cur)) continue;
      visited.add(cur);
      comp.push(cur);
      edges.forEach(e => {
        if (e.from === cur && !visited.has(e.to)) stack.push(e.to);
        if (e.to === cur && !visited.has(e.from)) stack.push(e.from);
      });
    }
    components.push(comp);
  });

  const nodeMap = {};
  const componentCenters = {};
  const numComps = components.length || 1;

  // Place each component at a different sector of the radial layout
  if (numComps > 1) {
    components.forEach((comp, ci) => {
      const compAngle = (2 * Math.PI * ci / numComps) - Math.PI / 2;
      const compCx = cx + radius * 0.5 * Math.cos(compAngle);
      const compCy = cy + radius * 0.5 * Math.sin(compAngle);
      componentCenters[comp[0]] = { x: compCx, y: compCy };

      // Within each component, sort by degree and place radially
      const compSorted = [...comp].sort((a, b) => (degree[b]||0) - (degree[a]||0));
      compSorted.forEach((n, i) => {
        const innerR = i === 0 ? 0 : 50 + (i / compSorted.length) * radius * 0.4;
        const a = (2 * Math.PI * i / Math.max(compSorted.length, 1));
        nodeMap[n] = {
          x: compCx + innerR * Math.cos(a),
          y: compCy + innerR * Math.sin(a),
          vx: 0, vy: 0, label: n, name: n,
        };
      });
    });
  } else {
    // Single component — root at center, children radiate outward
    const hub = sorted[0] || nodeList[0];
    nodeMap[hub] = { x: cx, y: cy, vx: 0, vy: 0, label: hub, name: hub };
    for (let i = 1; i < sorted.length; i++) {
      const angle = (2 * Math.PI * i / (sorted.length - 1)) - Math.PI / 2;
      const r = radius * (0.3 + 0.7 * (i / sorted.length));
      nodeMap[sorted[i]] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        vx: 0, vy: 0, label: sorted[i], name: sorted[i],
      };
    }
  }

  // Ensure all nodes are in the map (handles isolated ones)
  Object.keys(nodeMap).forEach(n => { if (!nodeList.includes(n)) delete nodeMap[n]; });
  nodeList.forEach(n => {
    if (!nodeMap[n]) {
      const angle = Math.random() * Math.PI * 2;
      nodeMap[n] = { x: cx + radius * 0.5 * Math.cos(angle), y: cy + radius * 0.5 * Math.sin(angle), vx: 0, vy: 0, label: n, name: n };
    }
  });

  let totalIterations = 0;
  const maxIterations = 800;
  const nodeCount = nodeList.length;
  const idealDist = Math.min(w, h) / (Math.sqrt(nodeCount) + 2);

  function runForceLayout(batchSize) {
    for (let iter = 0; iter < batchSize; iter++) {
      if (totalIterations >= maxIterations) break;
      const alpha = 1.0 - totalIterations / maxIterations;
      const repBase = idealDist * idealDist * 2.5;
      const springLen = idealDist * 1.8;

      // Stronger repulsion to prevent clustering
      for (const a of Object.values(nodeMap)) {
        for (const b of Object.values(nodeMap)) {
          if (a === b) continue;
          let dx = a.x - b.x || 0.01, dy = a.y - b.y || 0.01;
          let d2 = dx*dx + dy*dy;
          let dist = Math.sqrt(d2);
          // Min distance floor to prevent infinite forces
          let effectiveD2 = Math.max(d2, 50 * 50);
          let force = repBase / effectiveD2;
          a.vx += (dx/dist)*force*alpha;
          a.vy += (dy/dist)*force*alpha;
        }
      }

      // Spring attraction along edges
      for (const e of edges) {
        const a = nodeMap[e.from], b = nodeMap[e.to];
        if (!a || !b) continue;
        let dx = b.x - a.x, dy = b.y - a.y;
        let dist = Math.sqrt(dx*dx + dy*dy) || 1;
        let force = (dist - springLen) * 0.04 * alpha;
        a.vx += (dx/dist)*force;
        a.vy += (dy/dist)*force;
        b.vx -= (dx/dist)*force;
        b.vy -= (dy/dist)*force;
      }

      // Weak center gravity — just to keep nodes on canvas, not clustered
      for (const n of Object.values(nodeMap)) {
        const distToCenter = Math.sqrt((n.x-cx)**2 + (n.y-cy)**2);
        const canvasR = Math.min(w, h) * 0.45;
        if (distToCenter > canvasR) {
          n.vx += (cx - n.x) * 0.03;
          n.vy += (cy - n.y) * 0.03;
        }
      }

      // Integrate with moderate damping
      for (const n of Object.values(nodeMap)) {
        n.vx *= 0.6;
        n.vy *= 0.6;
        n.x += Math.max(-40, Math.min(40, n.vx));
        n.y += Math.max(-40, Math.min(40, n.vy));
        // Keep within canvas bounds
        n.x = Math.max(60, Math.min(w - 60, n.x));
        n.y = Math.max(80, Math.min(h - 80, n.y));
      }

      totalIterations++;
    }

    if (totalIterations < maxIterations) {
      runForceLayout(batchSize);
    } else {
      for (const n of Object.values(nodeMap)) { n.vx = 0; n.vy = 0; }
    }
  }

  // Run initial burst fast, then settle
  runForceLayout(300);

  // Edge type → color mapping
  const edgeColors = {
    prerequisite: 'rgba(108,92,231,',
    enables: 'rgba(0,206,201,',
    contradicts: 'rgba(253,121,168,',
    generalizes: 'rgba(255,234,167,',
    specializes: 'rgba(225,112,85,',
    analogous_to: 'rgba(162,155,254,',
    historically_follows: 'rgba(250,177,160,',
  };

  const hitAreas = [];
  let hoveredNode = null;

  function roundRect(ctx, x, y, w, h, r) {
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);   ctx.arcTo(x + w, y,     x + w, y + r, r);
    ctx.lineTo(x + w, y + h - r); ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
    ctx.lineTo(x + r, y + h);   ctx.arcTo(x,     y + h, x,     y + h - r, r);
    ctx.lineTo(x, y + r);       ctx.arcTo(x,     y,     x + r, y,     r);
    ctx.closePath();
  }

  function drawNode(n, isHighDeg) {
    const r = isHighDeg ? 18 : 14;

    ctx.save();
    ctx.shadowColor = 'rgba(108,92,231,.6)';
    ctx.shadowBlur = 14;

    // Circle body
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI*2);
    ctx.fillStyle = isHighDeg ? 'rgba(108,92,231,0.25)' : 'rgba(255,255,255,0.06)';
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = n._hovered ? 'rgba(108,92,231,.8)' : 'rgba(255,255,255,0.12)';
    ctx.lineWidth = (n._hovered || isHighDeg) ? 2.2 : 1.5;
    ctx.stroke();

    // Short label inside circle
    ctx.font = isHighDeg ? '600 11px Inter, sans-serif' : '400 10px Inter, sans-serif';
    ctx.fillStyle = '#e4e6eb';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const shortLabel = n.label.length > 8 ? n.label[0] + '\u2026' : n.label;
    ctx.fillText(shortLabel, n.x, n.y);

    // Full label pill below circle
    const words = n.label.split(' ');
    let lines = [];
    let cur = '';
    words.forEach(word => {
      if ((cur + ' ' + word).trim().length > 15) {
        lines.push(cur.trim());
        cur = word;
      } else {
        cur = (cur + ' ' + word).trim();
      }
    });
    lines.push(cur.trim());

    const lineH = 12;
    const longestLine = lines.reduce((a,b) => a.length > b.length ? a : b, '');
    const pillW = ctx.measureText(longestLine).width + 10;
    const pillH = lines.length * lineH + 6;

    // Pill background
    const px = n.x - pillW/2;
    const py = n.y + r + 4;
    ctx.fillStyle = 'rgba(0,0,0,.5)';
    ctx.beginPath();
    roundRect(ctx, px, py, pillW, pillH, 3);
    ctx.fill();

    // Pill text
    ctx.font = '500 10px Inter, sans-serif';
    ctx.fillStyle = n._hovered ? '#fff' : 'rgba(255,255,255,.85)';
    lines.forEach((line, li) => {
      const midLine = Math.ceil(lines.length / 2);
      if (lines.length === 1 || li >= midLine) ctx.textBaseline = 'top';
      else ctx.textBaseline = 'bottom';
      ctx.fillText(line, n.x, py + 3 + (li * lineH));
    });

    hitAreas.push({
      name: n.name, x: px, y: py, w: pillW, h: pillH,
      cx: n.x, cy: n.y, rr: r,
    });
    ctx.restore();
  }

  function draw() {
    Object.values(nodeMap).forEach(n => n._hovered = false);
    if (hoveredNode) nodeMap[hoveredNode.name]._hovered = true;
    hitAreas.length = 0;

    ctx.clearRect(0, 0, w, h);

    // Edges
    edges.forEach(e => {
      const a = nodeMap[e.from], b = nodeMap[e.to];
      if (!a || !b) return;

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      const col = edgeColors[e.type] || 'rgba(150,156,180,';
      ctx.strokeStyle = col + '0.5)';
      ctx.lineWidth = 1.4;
      ctx.stroke();

      // Arrowhead at midpoint
      const mx2 = (a.x+b.x)/2, my2 = (a.y+b.y)/2;
      const angle = Math.atan2(b.y - a.y, b.x - a.x);
      const arrowLen = 5;
      ctx.beginPath();
      ctx.moveTo(mx2 + Math.cos(angle)*arrowLen*1.5, my2 + Math.sin(angle)*arrowLen*1.5);
      ctx.moveTo(mx2 - Math.cos(angle-0.6)*arrowLen*1.5, my2 - Math.sin(angle-0.6)*arrowLen*1.5);
      ctx.lineTo(mx2 - Math.cos(angle+0.6)*arrowLen*1.5, my2 - Math.sin(angle+0.6)*arrowLen*1.5);
      ctx.strokeStyle = col + '0.7)';
      ctx.lineWidth = 1.2;
      ctx.stroke();

      if (e.type === 'prerequisite' || e.type === 'enables') {
        ctx.save();
        ctx.font = '600 9px Inter, sans-serif';
        ctx.fillStyle = col + '0.7)';
        ctx.textAlign = 'center';
        ctx.fillText(e.type.replace('_', ' '), mx2, my2 - 8);
        ctx.restore();
      }
    });

    // Nodes
    Object.values(nodeMap).forEach(n => {
      const isHighDeg = edges.filter(e=>e.from===n.name||e.to===n.name).length >= 3;
      drawNode(n, isHighDeg);
    });

    // Tooltip for hovered node
    if (hoveredNode && nodeMap[hoveredNode.name]) {
      const hn = nodeMap[hoveredNode.name];
      const conn = edges.filter(e => e.from === hoveredNode.name || e.to === hoveredNode.name);
      if (conn.length) {
        const tips = conn.slice(0, 3).map(e =>
          e.type.replace('_', ' ') + ': ' + (e.from === hoveredNode.name ? e.to : e.from)
        );
        const tooltip = tips.join(' · ') + (conn.length > 3 ? ` +${conn.length-3} more` : '');
        ctx.save();
        ctx.font = '400 9px Inter, sans-serif';
        const tw = ctx.measureText(tooltip).width + 12;
        ctx.fillStyle = 'rgba(25,25,35,.88)';
        ctx.beginPath();
        roundRect(ctx, hn.cx - tw/2, hn.cy - 30, tw, 18, 4);
        ctx.fill();
        ctx.strokeStyle = 'rgba(108,92,231,.3)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = '#ccc';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(tooltip, hn.cx, hn.cy - 27);
        ctx.restore();
      }
    }

    // Fade-in animation (one shot)
    const wrapper = canvas.parentElement;
    if (wrapper.style.opacity !== '1') {
      wrapper.style.transition = 'opacity .4s';
      wrapper.style.opacity = '1';
    }
  }

  // Hover listeners
  canvas.addEventListener('mousemove', (evt) => {
    const rect = canvas.getBoundingClientRect();
    const mx = evt.clientX - rect.left;
    const my = evt.clientY - rect.top;
    let hit = null;
    for (const h of hitAreas) {
      if (mx >= h.x && mx <= h.x + h.w && my >= h.y - h.rr && my <= h.y + h.h) { hit = h; break; }
      if (Math.hypot(mx - h.cx, my - h.cy) <= 22) { hit = h; break; }
    }
    if (hit !== hoveredNode) {
      hoveredNode = hit;
      draw();
    }
  });

  canvas.addEventListener('mouseleave', () => {
    hoveredNode = null;
    draw();
  });

  // Animate in
  canvas.parentElement.style.opacity = '0';
  let t0 = Date.now();
  function animIn() {
    if (Date.now() - t0 < 200) { requestAnimationFrame(animIn); return; }
    draw();
  }
  animIn();
}


/* ─── Helpers ───────────────────────────── */

function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

