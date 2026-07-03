# ADR-009 — Louvain community detection runs client-side, live

**Status:** Accepted (2026-07-02)

## Context
`music-project.md` calls for Louvain communities rendered as color clusters, but not
*where* they are computed. Two options:

- **Baked in Python:** compute communities once at export time, add a `community` field per
  node. Simple, but frozen to one weighting — the moment the user changes the genre/year
  weights, metric, threshold, or draw mode, the coloring no longer matches the graph on
  screen. This contradicts the project's core architecture (ADR-002): per-axis similarities
  precomputed, the *weighted combination* done live client-side so tuning is real-time.
- **Client-side, live:** run Louvain in the browser on the currently-drawn weighted graph,
  recomputing when the graph topology changes (control changes, not per animation tick).
  Communities recolor as you retune — the coloring always describes what you're looking at.

Empirically the choice matters: on the 40-album set, Louvain at default 50/50 genre/year
weights finds **era-driven** communities (1990s vs 2000s split, each mixing genres), while
at genre-only weights it recovers **clean genre communities** (shoegaze / black metal /
hip-hop / jazz / folk / ambient / post-rock). A baked assignment would hide this; the live
version surfaces it as you move the year slider.

## Decision
- **Compute Louvain client-side, live** (`frontend/louvain.js`), on the active (drawn) edge
  set weighted by the live similarity score. Recompute on control changes only, not per tick.
- **No export-schema change** — communities are derived client-side from the same edges +
  weights already shipped. `dominant_tag` stays in the export and remains selectable via a
  `Color by: community | tag` toggle.
- **Stable coloring:** communities are ranked by their smallest member id and colored by rank,
  so a cluster keeps its color across slider tweaks despite Louvain's raw labels churning.
- **Legend** labels each community by its majority `dominant_tag` (+ size), giving the
  otherwise-anonymous clusters a human name.

## Consequences
- Coloring always matches the on-screen graph; communities become another live lens, not a
  frozen attribute — consistent with the A/B-by-eye workflow.
- Louvain is near-linear and trivial at ≤5k nodes; recomputing on control change (not per
  frame) keeps it cheap. If it ever bites at scale, move to a Web Worker or precompute a
  cache — profile first (Performance rules), don't pre-optimize.
- **Interaction to know:** at the 50/50 default, communities read as *eras*, not genres,
  because the year kernel (σ=5) makes same-era albums densely connected. Slide year → 0 for
  genre communities. Whether the *default* weighting should lean genre is a separate,
  still-open tuning question (config `DEFAULTS`) — deliberately left to the slider for now.
- Own, dependency-free Louvain (no graphology/jLouvain vendor); validated by
  `tools/louvain_check.js` against the known genre clusters.
