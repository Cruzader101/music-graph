# ADR-008 — Export schema as a self-describing contract

**Status:** Accepted (2026-07-02)

## Context
The frontend consumes exported JSON only — the sole coupling to the Python side (music-project.md). The
schema must carry everything the client needs to render, run all metric/draw toggles, and
initialize sliders consistently with what Python computed — while staying decoupled from Python
internals. It also has to render meaningfully *before* Louvain (no community colors) and scoring
(no node sizes) exist.

## Decision
- Single self-describing JSON: `meta` + `nodes` + `edges`, documented canonically in
  `docs/export-schema.md`.
- **`meta`** carries `pipeline_version`, slider `defaults`, `export_floor`, `top_k_guarantee`, and
  default toggle positions — so the graph reproduces and sliders initialize to Python's values.
- **Nodes** keyed by normalized string id; carry `dominant_tag` (interim community color until
  Louvain) and `year` + `year_status`.
- **Edges** carry the 4 `sim_genre_*` values + `sim_year`; `sim_year: null` is the per-edge signal
  to drop the year term and renormalize (client-side, ADR-002) — no cross-referencing node state.
- The **field shape is full from day one** even though the thin first run only populates
  `sim_genre_raw_cosine` + `sim_year` (build cut line): growing the schema later would be a
  coordinated two-sided change, which the contract rule says to avoid.

## Consequences
- Frontend is fully decoupled: everything it needs travels in the file.
- Adding an axis = new edge field + slider, deliberately.
- Node-by-id (not index) is robust to reordering and debuggable; JSON size is a non-issue at ≤5k.
- `docs/export-schema.md` is the single source of truth; changes there are the contract changing.
