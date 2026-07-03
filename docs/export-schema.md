# Export Schema — the frontend↔backend contract

This is the **one place** the export schema is documented (per music-project.md). The Python export
stage writes exactly this; the frontend consumes exactly this and nothing else. Change it
deliberately — a change here is a coordinated change on both sides. Adopted in ADR-008.

## Shape

```jsonc
{
  "meta": {
    "pipeline_version": "1",
    "generated": "2026-07-02T12:00:00Z",
    "album_count": 100,
    "defaults": {                 // frontend initializes sliders to these
      "w_genre": 0.5,
      "w_year": 0.5,
      "sigma_year": 5,            // gaussian year kernel width (informational; sim_year already baked)
      "threshold": 0.35,
      "k": 8
    },
    "export_floor": 0.15,         // edge shipped if max axis >= floor OR in either endpoint's top-15
    "top_k_guarantee": 15,        // => client k slider ranges 1..15
    "genre_metric_default": "cosine",     // cosine | jaccard
    "genre_weighting_default": "raw",     // raw | idf
    "draw_mode_default": "threshold"      // threshold | knn | mutual_knn
  },

  "nodes": [
    {
      "id": "my bloody valentine␟loveless",  // normalized(artist)␟normalized(album) — primary key
      "artist": "My Bloody Valentine",       // display (original casing)
      "album": "Loveless",
      "dominant_tag": "shoegaze",            // highest-weight post-blacklist tag → node color
      "year": 1991,                          // int, or null
      "year_status": "resolved"              // resolved | unresolved
    }
  ],

  "edges": [
    {
      "source": "my bloody valentine␟loveless",  // node id
      "target": "slowdive␟souvlaki",
      "sim_genre_raw_cosine": 0.86,
      "sim_genre_raw_jaccard": 0.58,
      "sim_genre_idf_cosine": 0.79,
      "sim_genre_idf_jaccard": 0.51,
      "sim_year": 0.92                       // null ⇒ this pair drops the year term + renormalizes
    }
  ]
}
```

## Client responsibilities (derived, never shipped)

- **Weighted sum:** `sim = w_genre·sim_genre_<metric>_<weighting> + w_year·sim_year`, using the
  selected metric/weighting toggles. If `sim_year` is null, drop the year term and renormalize
  `w_genre` to 1 for that edge (ADR-002).
- **Drawing:** apply the selected mode (threshold / knn / mutual_knn) to the live weighted score.
  All edges any mode could need are guaranteed present (ADR-004).
- **Color:** node by `dominant_tag`. **Labels:** zoom-adaptive, viewport-local density trigger.

## Invariants

- Every edge's endpoints exist in `nodes`.
- `sim_genre_*` ∈ [0,1]; `sim_year` ∈ [0,1] or null.
- Node `id` unique; reissues already collapsed upstream (ADR-007).
- First run populates only `sim_genre_raw_cosine` + `sim_year` meaningfully; other genre fields may
  be present-but-provisional until enabled (build cut line). Field *shape* is stable from day one.
