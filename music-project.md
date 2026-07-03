# Music Graph — Project Context

## What This Is

An Obsidian-style interactive graph of albums, where edges represent similarity. Similarity starts as **subgenre + year**, with a toggle system designed so new axes (vibe, lyrics, audio features) slot in later as additional weighted terms. On top of the graph: playlist generation (paths and walks through the graph) and a scoring system for rating albums.

Personal project, product-first: designed, built, and tuned by Cruz.

## Core Design

**Similarity model**
```
sim(a, b) = w_genre · sim_genre(a, b) + w_year · sim_year(a, b)   [+ future terms]
```
- `sim_year`: gaussian kernel `exp(-(Δyear)² / 2σ²)`, σ user-tunable (default 5)
- `sim_genre` v1: **both** weighted cosine and weighted Jaccard on Last.fm tag vectors, each in **raw and IDF-weighted** flavors (IDF df from Last.fm global `tag.getInfo`, not the local corpus). 4 genre values per edge; frontend `[cosine|jaccard]` × `[raw|idf]` toggles pick which feeds the sum (see ADR-005). Tag vectors filtered by a **blacklist** (ADR-003), not a whitelist
- `sim_genre` v2 (planned): genre co-occurrence embedding — SVD on the genre×genre co-occurrence matrix built from the album corpus, so related-but-non-overlapping genres (dream pop ↔ shoegaze) score as similar
- Weights `w_*` are the frontend toggles/sliders. Consequence: per-axis similarities are precomputed in Python and exported on each edge; the **weighted sum happens client-side** so sliders update live without recomputation. Export includes any edge whose max per-axis similarity clears a floor **OR** that is in either endpoint's top-15 neighbors (so client-side kNN/mutual-kNN are never starved — ADR-004)
- Missing data: if a pair lacks year data, drop the year term and **renormalize remaining weights** for that pair (otherwise missing-year albums get systematically weaker edges)

**Graph construction**
- Nodes: albums, keyed by `normalize(artist)␟normalize(album)` with reissue/edition suffixes stripped so remasters collapse to one node; Last.fm mbid stored as a merge aid (ADR-007). Edges: **all three** drawing rules — threshold / kNN / mutual-kNN — shipped as a live client-side toggle over the same exported edges (ADR-004)
- Community detection: Louvain, communities rendered as color clusters
- Layout: d3-force initially; sigma.js if node count makes d3 choke

**Playlists = graph traversals**
- Path playlist: shortest path between two chosen albums (smooth transition)
- Vibe playlist: random walk constrained to a community
- Deferred until graph v1 works

**Scoring** (active workstream)
- Elo-style pairwise rating: Cruz is shown two albums, picks a winner, ratings update via standard Elo. Better calibrated than 1–10 scales and converges fast with smart pair selection (prefer pairs with close ratings / high uncertainty)
- Store full comparison history in SQLite (`comparisons` table: album_a, album_b, winner, timestamp) so the rating model can be swapped later (Elo → Bradley-Terry or TrueSkill) without losing data
- Downstream use: scores rendered as node size/brightness in the graph; later, bias playlist walks toward high-rated regions

## Data Sources

**Last.fm API (primary)** — one client, one cache path, one auth.

- Genre/vibe tags: `album.getTopTags` — weighted, per-album normalized (top tag = 100). ~5 req/s limit. Filtered by a **blacklist** of junk tags (`seen live`, `albums I own`, bare decades); IDF handles over-common generic tags separately (ADR-003)
- Global tag frequencies: `tag.getInfo` (taggings/reach) — the df source for IDF weighting (ADR-005), cached per distinct tag
- Album metadata: `album.getInfo`

**MusicBrainz (year supplement only)** — Last.fm's release-date data is deprecated/spotty, and year is half the similarity model.

- Year resolution order: Last.fm year if present → MusicBrainz `release-group` search (artist + album). **Conservative matching** (ADR-006): accept only if fuzzy-artist matches AND search score clears a floor; among qualifying release-groups take the **earliest** `first-release-date` (defeats reissues dating a 1985 album to 2011). Else flag `year_unresolved` — node still renders, year term dropped and weights renormalized (see similarity model). Principle: a wrong year mis-places a node, a missing year degrades gracefully — so refuse to guess
- No auth, 1 req/s limit — fine with caching. Do not use MusicBrainz for anything besides years without an ADR.

**Not used:** Spotify (audio-features endpoint dead for new apps since late 2024), Wikipedia (infobox parsing too fragile vs. MusicBrainz's structured `first-release-date`).

**Future "vibe" axis:** own audio analysis via librosa/Essentia (Cruz has prior FMA pipeline experience).

**Caching is mandatory**: every raw API response stored in SQLite before transformation. Refetching is a failure mode.

## Album Set

TBD — either Cruz's library export or a seeded canonical list. Target scale assumption: **≤ 5k albums** (keeps O(n²) similarity trivial). Revisit architecture if this grows.

## Stack

- **Python 3.14** (`C:\Python314\python.exe`), numpy/scipy/pandas for pipeline
- **SQLite** for cache + derived features
- **Frontend**: static page, d3-force graph; per-axis similarities precomputed in Python and exported as JSON, weighted sum + threshold applied client-side (this is what makes the sliders live)
- Dev on Windows — mind PATH issues, dev directory outside OneDrive (`C:\dev`)

## Status / Roadmap

**First milestone — vertical slice (one-shot target):** ~100 albums end-to-end: fetch → clean → similarity v1 → graph JSON → rendered d3 graph with weight sliders. Everything below is iteration on that skeleton.

1. ☑ Vertical slice (fetchers + cache, blacklist cleaning, cosine+jaccard genre + year kernel, JSON export, d3 frontend) — PASSES on 40-album seed (2026-07-02); see devlog + acceptance-thin-slice.md
2. ☐ Coverage audit tooling (tag coverage %, junk leakage, missing years)
3. ☐ Scale album set toward full target
4. ☐ Genre co-occurrence embedding (similarity v2)
5. ☐ Louvain communities + coloring
6. ☐ Scoring system: comparison history schema + Elo updates + pair selection, node size/brightness in graph
7. ☐ Playlists (paths, walks) — later: bias walks by score

## Decisions Log

Architecture decisions get ADRs in `docs/adr/`. Current standing decisions:
- **ADR-001**: Last.fm primary source; MusicBrainz for release years only (chosen over Wikipedia — structured field vs. infobox parsing)
- **ADR-002**: similarity as weighted sum of per-axis similarities, weights exposed as UI toggles; missing axis → renormalize surviving weights per-pair
- **ADR-003**: tag filtering by **blacklist + IDF**, reversing the original whitelist decision (IDF absorbed the whitelist's second job; a strict allow-list dropped niche signal on a curated corpus)
- **ADR-004**: edge construction — all three drawing modes (threshold/kNN/mutual-kNN) client-side; export floor OR per-node top-15 guarantee to avoid starvation
- **ADR-005**: genre metric strategy — dual metric (cosine+jaccard) × dual weighting (raw+IDF), corpus-aware IDF from Last.fm global tag frequencies
- **ADR-006**: conservative MusicBrainz year resolution — verify-or-flag, earliest qualifying release date, missing over wrong
- **ADR-007**: album identity — normalized `(artist, album)` key with reissue suffixes stripped, mbid as merge aid
