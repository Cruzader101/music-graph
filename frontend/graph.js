/* Music Graph frontend. Consumes graph.json (docs/export-schema.md) and nothing
 * else. All the tuning is client-side over precomputed per-axis similarities:
 *   score = w_genre·sim_genre_<metric>_<weighting> + w_year·sim_year
 * with per-edge renormalization when sim_year is null (ADR-002). Draw modes
 * (threshold / kNN / mutual kNN) filter the live score (ADR-004). */

const svg = d3.select("#graph");
const gRoot = svg.append("g");
const gLinks = gRoot.append("g");
const gNodes = gRoot.append("g");
const gLabels = gRoot.append("g");

let W = 0, H = 0;
function size() {
  const r = document.getElementById("stage").getBoundingClientRect();
  W = r.width; H = r.height;
  svg.attr("viewBox", [0, 0, W, H]);
}
size();
window.addEventListener("resize", () => { size(); sim && sim.alpha(0.3).restart(); });

const controls = {
  w_genre: 0.5, w_year: 0.5,
  metric: "cosine", weighting: "raw", mode: "threshold",
  threshold: 0.35, k: 8, colorby: "community",
};

// Stable categorical palette for communities (indexed by stable rank).
const COMM_PALETTE = d3.schemeCategory10.concat(d3.schemeSet3, d3.schemePaired);

let nodes = [], edges = [], tagColor = null, sim = null;
let communityMeta = new Map();  // communityId -> {rank, color, label, size}
let linkSel, nodeSel, labelSel;
let zoomK = 1;
let focus = null; // hovered node id

// --- Similarity scoring (mirror of the client contract) --------------------
function edgeScore(e) {
  const g = e[`sim_genre_${controls.weighting}_${controls.metric}`];
  const y = e.sim_year;
  const wg = controls.w_genre, wy = controls.w_year;
  if (y === null || y === undefined) {
    return g == null ? 0 : g;                     // year dropped → genre carries the edge (ADR-002)
  }
  const denom = wg + wy;
  if (denom === 0) return 0;
  return (wg * (g ?? 0) + wy * y) / denom;
}

// --- Draw-mode filtering ---------------------------------------------------
function activeEdges() {
  const scored = edges.map(e => ({ e, s: edgeScore(e) }));
  if (controls.mode === "threshold") {
    return scored.filter(d => d.s >= controls.threshold);
  }
  // Build per-node top-k neighbor sets by live score.
  const nbr = new Map();
  nodes.forEach(n => nbr.set(n.id, []));
  for (const { e, s } of scored) {
    nbr.get(e.source.id ?? e.source).push({ o: e.target.id ?? e.target, s });
    nbr.get(e.target.id ?? e.target).push({ o: e.source.id ?? e.source, s });
  }
  const topk = new Map();
  for (const [id, list] of nbr) {
    list.sort((a, b) => b.s - a.s);
    topk.set(id, new Set(list.slice(0, controls.k).map(d => d.o)));
  }
  return scored.filter(({ e }) => {
    const a = e.source.id ?? e.source, b = e.target.id ?? e.target;
    const aHasB = topk.get(a).has(b), bHasA = topk.get(b).has(a);
    return controls.mode === "knn" ? (aHasB || bHasA) : (aHasB && bHasA);
  });
}

// --- Render ----------------------------------------------------------------
function render() {
  const active = activeEdges();
  document.getElementById("edge-count").textContent = active.length;
  const links = active.map(({ e, s }) => ({ source: e.source, target: e.target, score: s }));

  recomputeCommunities(links);   // live Louvain on the currently-drawn weighted graph (ADR-009)
  applyNodeColors();
  buildLegend();

  linkSel = gLinks.selectAll("line").data(links, d =>
    `${d.source.id ?? d.source}|${d.target.id ?? d.target}`);
  linkSel.exit().remove();
  linkSel = linkSel.enter().append("line").attr("class", "link").merge(linkSel)
    .attr("stroke-width", d => 0.5 + 2.5 * d.score);

  sim.nodes(nodes);
  sim.force("link").links(links);
  sim.alpha(0.6).restart();
  updateFocusStyles();
}

function ticked() {
  linkSel
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);
  positionLabels();
}

// --- Zoom-adaptive labels: viewport-local density thinning -----------------
// When zoomed out, only the highest-degree node in each ~110px screen cell is
// labeled; past a zoom threshold, all in-viewport nodes get labels. Hovered
// node + neighbors always labeled.
const LABEL_ZOOM_ALL = 1.6;
const CELL = 110;
function visibleLabelSet() {
  const show = new Set();
  const t = d3.zoomTransform(svg.node());
  const inView = n => {
    const x = t.applyX(n.x), y = t.applyY(n.y);
    return x > -20 && x < W + 20 && y > -20 && y < H + 20;
  };
  if (zoomK >= LABEL_ZOOM_ALL) {
    nodes.forEach(n => { if (inView(n)) show.add(n.id); });
  } else {
    const best = new Map(); // cell → node with max degree
    for (const n of nodes) {
      if (!inView(n)) continue;
      const cx = Math.floor(t.applyX(n.x) / CELL), cy = Math.floor(t.applyY(n.y) / CELL);
      const key = `${cx},${cy}`;
      const cur = best.get(key);
      if (!cur || (n.degree || 0) > (cur.degree || 0)) best.set(key, n);
    }
    best.forEach(n => show.add(n.id));
  }
  if (focus) {
    show.add(focus);
    (neighborsOf.get(focus) || []).forEach(id => show.add(id));
  }
  return show;
}

function positionLabels() {
  const show = visibleLabelSet();
  labelSel
    .attr("transform", d => `translate(${d.x + 7},${d.y + 4})`)
    .attr("display", d => show.has(d.id) ? null : "none");
}

// --- Focus / hover highlighting -------------------------------------------
let neighborsOf = new Map();
function recomputeNeighbors(links) {
  neighborsOf = new Map(nodes.map(n => [n.id, new Set()]));
  links.forEach(l => {
    const a = l.source.id ?? l.source, b = l.target.id ?? l.target;
    neighborsOf.get(a).add(b); neighborsOf.get(b).add(a);
  });
}
function updateFocusStyles() {
  const dim = focus != null;
  nodeSel.classed("dim", d => dim && d.id !== focus && !(neighborsOf.get(focus)?.has(d.id)));
  linkSel.classed("dim", d => {
    if (!dim) return false;
    const a = d.source.id ?? d.source, b = d.target.id ?? d.target;
    return a !== focus && b !== focus;
  });
  positionLabels();
}

// --- Boot ------------------------------------------------------------------
fetch("graph.json").then(r => r.json()).then(graph => {
  nodes = graph.nodes.map(n => ({ ...n }));
  edges = graph.edges;

  // init controls from meta.defaults
  const d = graph.meta.defaults;
  controls.w_genre = d.w_genre; controls.w_year = d.w_year;
  controls.threshold = d.threshold; controls.k = d.k;
  controls.metric = graph.meta.genre_metric_default;
  controls.weighting = graph.meta.genre_weighting_default;
  controls.mode = graph.meta.draw_mode_default;

  // URL params override defaults for shareable views, e.g.
  // ?w_genre=0.8&w_year=0.2&mode=knn&colorby=community
  const params = new URLSearchParams(location.search);
  for (const key of ["w_genre", "w_year", "threshold", "k"])
    if (params.has(key)) controls[key] = +params.get(key);
  for (const key of ["metric", "weighting", "mode", "colorby"])
    if (params.has(key)) controls[key] = params.get(key);
  syncControlsToUI();
  document.getElementById("meta-line").textContent =
    `${graph.meta.album_count} albums · ${edges.length} candidate edges · v${graph.meta.pipeline_version}`;

  // tag color scale (used when "color by: tag")
  const tags = Array.from(new Set(nodes.map(n => n.dominant_tag))).sort();
  const palette = d3.quantize(t => d3.interpolateSinebow(t * 0.92), Math.max(tags.length, 2));
  tagColor = d3.scaleOrdinal(tags, palette);

  // precompute degree from full candidate edge set (for label priority)
  const deg = new Map(nodes.map(n => [n.id, 0]));
  edges.forEach(e => { deg.set(e.source, (deg.get(e.source) || 0) + 1); deg.set(e.target, (deg.get(e.target) || 0) + 1); });
  nodes.forEach(n => n.degree = deg.get(n.id) || 0);

  nodeSel = gNodes.selectAll("g").data(nodes, n => n.id).enter().append("g").attr("class", "node");
  nodeSel.append("circle")
    .attr("r", n => 5 + Math.sqrt(n.degree))
    .attr("fill", "#888")   // recolored by applyNodeColors() on first render
    .on("mouseenter", (ev, n) => { focus = n.id; updateFocusStyles(); })
    .on("mouseleave", () => { focus = null; updateFocusStyles(); })
    .call(d3.drag()
      .on("start", (ev, n) => { if (!ev.active) sim.alphaTarget(0.3).restart(); n.fx = n.x; n.fy = n.y; })
      .on("drag", (ev, n) => { n.fx = ev.x; n.fy = ev.y; })
      .on("end", (ev, n) => { if (!ev.active) sim.alphaTarget(0); n.fx = null; n.fy = null; }));

  labelSel = gLabels.selectAll("text").data(nodes, n => n.id).enter().append("text")
    .attr("class", "label").text(n => `${n.artist} — ${n.album}`);

  sim = d3.forceSimulation(nodes)
    // Weak edges push far, strong edges pull tight → communities separate.
    .force("link", d3.forceLink().id(n => n.id).distance(l => 45 + 190 * (1 - l.score)).strength(l => 0.08 + 0.9 * l.score))
    .force("charge", d3.forceManyBody().strength(-420).distanceMax(700))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("x", d3.forceX(W / 2).strength(0.04))
    .force("y", d3.forceY(H / 2).strength(0.04))
    .force("collide", d3.forceCollide().radius(n => 14 + Math.sqrt(n.degree)))
    .on("tick", ticked);

  const zoom = d3.zoom().scaleExtent([0.2, 6]).on("zoom", ev => {
    gRoot.attr("transform", ev.transform); zoomK = ev.transform.k; positionLabels();
  });
  svg.call(zoom);

  // re-render on control change; recompute neighbor sets after each render's links
  sim.on("tick.neighbors", null);
  const origRender = render;
  window.render = () => { origRender(); recomputeNeighbors(gLinks.selectAll("line").data()); };
  window.render();
});

// --- UI wiring -------------------------------------------------------------
function syncControlsToUI() {
  document.getElementById("w_genre").value = controls.w_genre;
  document.getElementById("w_year").value = controls.w_year;
  document.getElementById("threshold").value = controls.threshold;
  document.getElementById("k").value = controls.k;
  document.getElementById("wg-out").textContent = (+controls.w_genre).toFixed(2);
  document.getElementById("wy-out").textContent = (+controls.w_year).toFixed(2);
  document.getElementById("th-out").textContent = (+controls.threshold).toFixed(2);
  document.getElementById("k-out").textContent = controls.k;
  setRadio("metric", controls.metric); setRadio("weighting", controls.weighting); setRadio("mode", controls.mode);
}
function setRadio(name, val) {
  document.querySelectorAll(`input[name=${name}]`).forEach(r => r.checked = (r.value === val));
}
function bindRange(id, key, out, fmt) {
  document.getElementById(id).addEventListener("input", e => {
    controls[key] = key === "k" ? +e.target.value : +e.target.value;
    document.getElementById(out).textContent = fmt(controls[key]);
    window.render && window.render();
  });
}
bindRange("w_genre", "w_genre", "wg-out", v => v.toFixed(2));
bindRange("w_year", "w_year", "wy-out", v => v.toFixed(2));
bindRange("threshold", "threshold", "th-out", v => v.toFixed(2));
bindRange("k", "k", "k-out", v => v);
["metric", "weighting", "mode"].forEach(name =>
  document.querySelectorAll(`input[name=${name}]`).forEach(r =>
    r.addEventListener("change", e => { controls[name] = e.target.value; window.render && window.render(); })));

// Color-by toggle: only recolor + relabel legend — no recompute / no layout restart.
document.querySelectorAll("input[name=colorby]").forEach(r =>
  r.addEventListener("change", e => { controls.colorby = e.target.value; applyNodeColors(); buildLegend(); }));

// --- Communities (live Louvain) -------------------------------------------
function recomputeCommunities(links) {
  const llinks = links.map(l => ({
    source: l.source.id ?? l.source, target: l.target.id ?? l.target, weight: l.score,
  }));
  const comm = louvain(nodes.map(n => n.id), llinks);   // id -> raw community index

  const byComm = new Map();
  nodes.forEach(n => {
    const c = comm.get(n.id);
    n.community = c;
    if (!byComm.has(c)) byComm.set(c, []);
    byComm.get(c).push(n);
  });

  // Stable ranking: order communities by their smallest member id, so a cluster
  // keeps its color across slider tweaks even though Louvain's raw labels churn.
  const list = [...byComm.entries()].map(([c, members]) => ({
    c, members, key: members.map(m => m.id).sort()[0], size: members.length,
  })).sort((a, b) => a.key < b.key ? -1 : 1);

  communityMeta = new Map();
  list.forEach((cm, rank) => {
    const counts = {};
    cm.members.forEach(m => { counts[m.dominant_tag] = (counts[m.dominant_tag] || 0) + 1; });
    const label = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];  // majority tag
    communityMeta.set(cm.c, { rank, color: COMM_PALETTE[rank % COMM_PALETTE.length], label, size: cm.size });
  });
  document.getElementById("comm-count").textContent = list.length;
}

function nodeFill(n) {
  if (controls.colorby === "community") {
    const meta = communityMeta.get(n.community);
    return meta ? meta.color : "#888";
  }
  return tagColor(n.dominant_tag);
}

function applyNodeColors() {
  if (nodeSel) nodeSel.select("circle").attr("fill", nodeFill);
}

function addLegendRow(el, swatch, text) {
  const row = document.createElement("div"); row.className = "legend-row";
  const sw = document.createElement("span"); sw.className = "legend-swatch"; sw.style.background = swatch;
  const label = document.createElement("span"); label.textContent = text;
  row.append(sw, label); el.append(row);
}

function buildLegend() {
  const el = document.getElementById("legend");
  const title = document.getElementById("legend-title");
  el.innerHTML = "";
  if (controls.colorby === "community") {
    title.textContent = "Communities (majority tag)";
    [...communityMeta.values()].sort((a, b) => a.rank - b.rank)
      .forEach(m => addLegendRow(el, m.color, `${m.label} · ${m.size}`));
  } else {
    title.textContent = "Dominant tags";
    tagColor.domain().forEach(t => addLegendRow(el, tagColor(t), t));
  }
}
