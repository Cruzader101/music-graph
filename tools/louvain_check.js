/* Validate live-Louvain communities on the real graph.json at default settings
 * (w_genre=w_year=0.5, raw cosine, threshold 0.35) — mirrors the frontend's
 * scoring so the printed communities match what the page shows.
 * Run: node tools/louvain_check.js
 */
const fs = require("fs");
const path = require("path");
const { louvain } = require("../frontend/louvain.js");

const graph = JSON.parse(fs.readFileSync(path.join(__dirname, "../frontend/graph.json"), "utf8"));
const d = graph.meta.defaults;

function score(e) {
  const g = e.sim_genre_raw_cosine;
  const y = e.sim_year;
  if (y === null || y === undefined) return g ?? 0;
  const denom = d.w_genre + d.w_year;
  return (d.w_genre * (g ?? 0) + d.w_year * y) / denom;
}

const links = graph.edges
  .map(e => ({ source: e.source, target: e.target, weight: score(e) }))
  .filter(l => l.weight >= d.threshold);

const comm = louvain(graph.nodes.map(n => n.id), links);
const label = new Map(graph.nodes.map(n => [n.id, `${n.artist} — ${n.album}`]));

const groups = new Map();
for (const n of graph.nodes) {
  const c = comm.get(n.id);
  if (!groups.has(c)) groups.set(c, []);
  groups.get(c).push(label.get(n.id));
}

console.log(`threshold ${d.threshold}, ${links.length} edges → ${groups.size} communities\n`);
[...groups.values()].sort((a, b) => b.length - a.length).forEach((members, i) => {
  console.log(`community ${i + 1} (${members.length}):`);
  members.forEach(m => console.log("   " + m));
  console.log();
});
