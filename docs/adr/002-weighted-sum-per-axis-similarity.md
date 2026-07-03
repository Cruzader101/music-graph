# ADR-002 — Similarity as a weighted sum of precomputed per-axis similarities

**Status:** Accepted (formalized 2026-07-02; implicit since project start)

## Context
Similarity must combine multiple axes (genre, year, and future: vibe, lyrics, audio) and
let the user retune their relative importance live, without recomputing anything expensive.

## Decision
- `sim(a,b) = Σ_axis w_axis · sim_axis(a,b)`.
- **Per-axis similarities are precomputed in Python** and stored/exported on each edge.
- **The weighted sum happens client-side** — the `w_axis` are the frontend sliders/toggles,
  so retuning is a cheap linear pass over existing edges, never a recompute.
- **Missing-axis handling:** if a pair lacks data for an axis (e.g. no year), drop that term
  and **renormalize the surviving weights to sum to 1 for that pair** — so incomplete data is
  never penalized as dissimilarity.

## Consequences
- The expensive O(n²) work is done once, offline; sliders stay real-time.
- The export schema is a hard contract: edges carry each per-axis value. Adding an axis =
  adding a field + a slider, deliberately (see Code Quality: schema is a contract).
- Renormalization is per-pair, not global — only pairs touching missing data are affected.
- Enables A/B of alternative per-axis metrics by exporting them side by side (see ADR-005).
