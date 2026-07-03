/* Compact multi-level Louvain community detection (modularity maximization).
 * Self-contained, deterministic (fixed node iteration order), weighted.
 * Runs client-side on the currently-drawn weighted graph so communities recolor
 * live as sliders/mode change (ADR-009). Near-linear; fine well past 5k nodes.
 *
 * louvain(nodeIds, links) -> Map(nodeId -> communityIndex)
 *   nodeIds: string[]   links: {source, target, weight}[]  (undirected)
 * Isolated nodes (no active edge) each land in their own singleton community.
 */
function louvain(nodeIds, links) {
  const n = nodeIds.length;
  const index = new Map(nodeIds.map((id, i) => [id, i]));

  // Level-0 weighted graph: adjacency maps + self-loop weights (2·w convention).
  let adj = Array.from({ length: n }, () => new Map());
  let self = new Array(n).fill(0);
  let m2 = 0; // = 2m (total weight, doubled)
  for (const l of links) {
    const a = index.get(l.source), b = index.get(l.target);
    if (a === undefined || b === undefined) continue;
    const w = l.weight > 0 ? l.weight : 1e-6;
    m2 += 2 * w;
    if (a === b) { self[a] += 2 * w; continue; }
    adj[a].set(b, (adj[a].get(b) || 0) + w);
    adj[b].set(a, (adj[b].get(a) || 0) + w);
  }

  const origToCur = nodeIds.map((_, i) => i); // original node → current super-node
  if (m2 === 0) return new Map(nodeIds.map((id, i) => [id, i])); // no edges → all singletons

  let curAdj = adj, curSelf = self, count = n;
  while (true) {
    const { comm, improved, nComm } = oneLevel(curAdj, curSelf, count, m2);
    for (let i = 0; i < n; i++) origToCur[i] = comm[origToCur[i]];
    if (!improved || nComm === count) break;

    // Aggregate communities into a new coarser graph.
    const nAdj = Array.from({ length: nComm }, () => new Map());
    const nSelf = new Array(nComm).fill(0);
    for (let i = 0; i < count; i++) {
      const ci = comm[i];
      nSelf[ci] += curSelf[i];
      for (const [j, w] of curAdj[i]) {
        if (comm[j] === ci) nSelf[ci] += w;            // internal (double-counted via symmetry → 2·w)
        else nAdj[ci].set(comm[j], (nAdj[ci].get(comm[j]) || 0) + w);
      }
    }
    curAdj = nAdj; curSelf = nSelf; count = nComm;
  }
  return new Map(nodeIds.map((id, i) => [id, origToCur[i]]));
}

function oneLevel(adj, self, count, m2) {
  const comm = Array.from({ length: count }, (_, i) => i);
  const k = new Array(count);                          // weighted degree incl. self-loop
  for (let i = 0; i < count; i++) { let s = self[i]; for (const [, w] of adj[i]) s += w; k[i] = s; }
  const sigmaTot = k.slice();                          // Σ degree per community

  let improved = false, moved = true, guard = 0;
  while (moved && guard++ < 100) {
    moved = false;
    for (let i = 0; i < count; i++) {
      const ci = comm[i];
      sigmaTot[ci] -= k[i];                            // pull i out of its community
      const wTo = new Map();                           // weight from i into each neighbor community
      for (const [j, w] of adj[i]) { const cj = comm[j]; wTo.set(cj, (wTo.get(cj) || 0) + w); }
      let bestC = ci, bestGain = (wTo.get(ci) || 0) - sigmaTot[ci] * k[i] / m2;
      for (const [cc, wic] of wTo) {
        const gain = wic - sigmaTot[cc] * k[i] / m2;   // ΔQ ∝ w_{i,C} − Σtot_C·k_i/2m
        if (gain > bestGain) { bestGain = gain; bestC = cc; }
      }
      comm[i] = bestC; sigmaTot[bestC] += k[i];
      if (bestC !== ci) { moved = true; improved = true; }
    }
  }
  const relabel = new Map(); let next = 0; const out = new Array(count);
  for (let i = 0; i < count; i++) {
    if (!relabel.has(comm[i])) relabel.set(comm[i], next++);
    out[i] = relabel.get(comm[i]);
  }
  return { comm: out, improved, nComm: next };
}

if (typeof module !== "undefined" && module.exports) module.exports = { louvain };
