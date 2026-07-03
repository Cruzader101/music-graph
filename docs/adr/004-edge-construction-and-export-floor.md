# ADR-004 — Edge construction (three modes, client-side) and the export floor

**Status:** Accepted (2026-07-02) — resolves the "threshold vs kNN, decision pending" note
in `music-project.md`.

## Context
Given a client-side weighted-sum score per pair, a rule must decide which pairs are drawn as
edges. Candidates: score **threshold**, **kNN** (top-k per node), **mutual kNN** (both list each
other). Each produces a different degree distribution and different failure modes:

- Threshold: uneven degree — hubs in dense genres, and isolated nodes (the "lonely flamenco
  record") float away with zero edges.
- kNN: uniform degree ≈ k, no islands, but forces weak edges in sparse regions.
- Mutual kNN: cleanest clusters, but can shatter the graph into disconnected components (bad for
  playlists, which need connectivity).

"Which feels right" is a judgment only the eye can make on the real corpus.

## Decision
- **Ship all three drawing modes as a live client-side toggle**, plus `k` and threshold sliders.
  They operate on the same exported edges and the same live weighted score — so switching modes
  changes *how edges are chosen*, never *what data exists*.
- **Export floor (Python):** an edge is written to the JSON if
  `max_axis_similarity(a,b) ≥ floor` **OR** the edge is among **either endpoint's top-15**
  neighbors (by best single axis). The floor captures threshold-mode's strong edges; the top-15
  guarantee feeds kNN/mutual-kNN so no node is *starved* (a drawing rule asking for an edge the
  export already deleted).
- `k` slider ranges 1..15 client-side.

## Consequences
- All three modes are honest for any slider setting: no edge pops in/out as an export artifact.
- JSON grows by ~15 edges/node worst case — trivial at ≤5k albums, never the full matrix.
- The export floor and the top-K guarantee are a **coupled contract** between the Python export
  and the frontend drawing rules; change them together.
- First run uses threshold only; kNN/mutual are wired-but-dark until the pipeline proves out
  end-to-end (see devlog / build cut line).
