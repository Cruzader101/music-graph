# Devlog

## 2026-07-03 — Session close / project state

Stopping the build here. **Where it stands:** vertical slice through Louvain communities is
working end-to-end on **250 real albums** (100% tag coverage, 98% years, 14 genre communities).
Roadmap 1, 2, 5 done; 3 stopped at 250 by choice; 4 (genre co-occurrence embedding), 6 (Elo
scoring), 7 (playlists) not started. Docs current: ADR-001..009, `music-project.md` Decisions Log
updated (008/009 added), ADR-003 amended with the scaling-era tag-filtering refinements, ADR-007
noted with the source-title-match class + prune behavior.

**To resume:** `python run.py` (all cached; ~instant) → open `frontend/index.html` via
`python -m http.server` in `frontend/`. Run `python -m tools.audit` after any `albums.csv` change.

**Two open threads (both decisions, not blockers):**
1. **Default weighting** — communities read as *eras* at the 50/50 default; set genre-leaning
   (`config.DEFAULTS`, e.g. w_genre 0.7 / w_year 0.3) if the first-load view should be genres.
2. **Elo scoring** (roadmap #6) — the last un-grilled design branch; grill it before building
   (pair selection, K-factor, cold start, sequencing) per the original design-mode approach.

Non-code: local static server was left running on :8777 during the session — harmless, dies with
the session.

## 2026-07-03 — Scaled to 250 albums (roadmap #3 — stopping point)

- **Done:** `data/albums.csv` 149 → **250** (+101 canonical albums: new territory — grunge, britpop, new-wave/synthpop, trip-hop, industrial, emo/midwest, reggae, art-pop — plus deepened hip-hop/jazz/electronic/metal/soul). Full run: **250/250 ok, 0 failed, 100% tag coverage, 98% years resolved** (6 unresolved), 11,266 edges. At genre-weighted kNN the graph resolves into **14 clean genre communities** (alt-rock, rap, electronic, shoegaze, jazz, folk, ambient, post-punk, post-rock, black metal, indie, idm, prog, soul). Neighbor spot-checks all defensible (Nirvana→In Utero/Alice in Chains; Portishead→Tricky/Massive Attack; Björk→Vespertine; Bob Marley→Burning Spear 0.995; American Football→Battles/Mineral/Slint).
- **Audit-driven fixes** (`tools/audit.py` again earned its keep): 3 title-match failures fixed (Art Blakey drop "& the Jazz Messengers"; GZA → GZA/Genius; Smashing Pumpkins → "The") → 0 sparse. Junk patterns in `clean.py` broadened to `^best…`, `…records$` (labels), `vinyl` → junk leakage down to 1 (legit `field recordings`).
- **Frontend:** added URL-param overrides for shareable views (`?w_genre=0.8&w_year=0.2&mode=knn&colorby=community`) — also how the 14-community view was captured.
- **Perf:** O(n²) at 250 = ~31k pairs; cosine matmul + Louvain still instant. No optimization needed.
- **Album-set scaling stops here at 250** (Cruz's call for this phase). Remaining open: default-weighting decision (era vs genre on load); Elo scoring branch (still un-grilled).

## 2026-07-02 — Scaled to 149 albums + coverage-audit tooling (roadmap #2, #3)

- **Done:** Grew `data/albums.csv` 40 → 149 (canonical, richly-tagged; deepened existing clusters and added post-punk / indie-alt / classic-prog / soul-funk / thrash-doom-death metal / more jazz-electronic, with deliberate bridges). Full run: **149/149 ok, 0 failed, 100% tag coverage (≥2 tags), 97% years resolved** (4 unresolved, all genuinely hard for MB's conservative match), 3854 edges. Neighbor spot-checks on the new clusters all defensible (Joy Division→Television/Cure/Wire; Marvin Gaye→Badu/Stevie/D'Angelo/Sly; Metallica→Slayer/Sabbath→Bathory; Pink Floyd→King Crimson/Tool).
- **Built `tools/audit.py`** (roadmap #2): fetch success, tag coverage %, sparse (<2 tag) albums, year resolution, and junk-tag leakage candidates → feeds the ADR-003 blacklist loop. Ran it, acted on it:
  - Junk *families* now killed by patterns in `clean.py` (not enumeration): `best of YEAR` / `best albums ever`, `…albums you must hear…`, and tags >45 chars (personal-narrative junk). Blacklisted `1001 albums you must hear before you die` (df=20), `where is my bong`, `perfect`.
  - Two title-match failures fixed: **Sly** needed `Sly & The Family Stone` (ampersand → funk/soul tags, was 0), **Eno** needed `Ambient 1: Music for Airports` (colon → ambient/electronic/minimalism, was 1 tag). Result: 0 sparse albums.
  - `fetch.py` now **prunes** albums removed from the CSV (so the Sly title change didn't orphan a node) — CSV is source of truth; not a fetch-failure drop.
- **Perf:** O(n²) at 149 = ~11k pairs, trivial; cosine matmul + Louvain both instant. Nothing to optimize.
- **Next:** default-weighting decision still open (era vs genre communities); scale further toward the ≤5k target, or open Elo scoring.

## 2026-07-02 — Louvain community coloring (client-side, live)

- **Done:** Roadmap #5. Own dependency-free multi-level Louvain (`frontend/louvain.js`), run client-side on the currently-drawn weighted graph and recomputed on control changes (ADR-009). Node color now = community (stable rank-based palette), with a `Color by: community | tag` toggle; legend labels each community by its majority dominant-tag + size. Collapses the old 20-color dominant-tag fragmentation to a handful of communities.
- **Validated:** `tools/louvain_check.js` (node) mirrors the frontend scoring. Genre-only weighting recovers textbook communities — shoegaze / black metal / hip-hop / jazz / folk / ambient / post-rock. Rendered + screenshotted; JS syntax clean.
- **Key finding:** communities track the live weights. At the **50/50 genre/year default they're era-driven** (90s vs 2000s, genre-mixed) because the year kernel (σ=5) densely links same-era albums; at year→0 they're clean genres. This is the live-Louvain payoff, but it means the default view's colors read as eras, not genres. **Open question for Cruz:** should default weighting lean genre (e.g. w_genre 0.7 / w_year 0.3), or drop σ_year? Left on the slider, not changed unilaterally (would touch a standing default).
- **Next:** decide default weighting; then scale the album set, or start the Elo scoring branch.

## 2026-07-02 — Vertical slice PASSES end-to-end on real data

- **Done:** Ran the full pipeline on the live Last.fm/MusicBrainz APIs over the 40-album seed set. `fetch` ok=40 failed=0, years via MusicBrainz (2 unresolved — Bill Evans live LP + GY!BE — correctly flagged, not guessed, per ADR-006). 134 tags, 407 candidate edges, `frontend/graph.json` rendered in Chrome headless.
- **Acceptance:** Check 1 (neighbor table) passes outright — all 8 seeds musically defensible, no junk neighbors (see `docs/acceptance-thin-slice.md`, table filled). Check 2 (visual) passes on spatial structure; color is fragmented because interim node color = dominant tag and one genre spans several tags — Louvain (roadmap #5) is the fix, not a metric bug.
- **Bugs caught + fixed mid-run:** (1) Last.fm `getInfo` `wiki.published` is the wiki EDIT date, not release date — it stamped Souvlaki as 2026; removed it, MusicBrainz is now the sole year source. (2) Kendrick's `good kid m.A.A.d city` (no comma) returned only label tags → isolated node; fixed title to `good kid, m.A.A.d city` (same normalized id). (3) Added record labels + "best of YEAR" to the blacklist (ADR-003 grow-as-spotted). (4) Normalized hyphen/space in tags so `hip-hop`≡`hip hop`, `post-rock`≡`post rock` (merges split cosine dims + colors).
- **Frontend:** tuned d3-force (charge -420, weak edges push far) so communities separate instead of hairballing; still connected at default threshold 0.35 (real cross-genre similarity) — kNN mode / higher threshold cleans it up.
- **Known/next:** interim color granularity → build Louvain communities (roadmap #5). Brian Eno — Ambient 1 has only 1 surviving tag (sparse; data-audit candidate). Then scale the album set past 40. idf/jaccard/kNN/mutual are all live toggles now (computed for real), raw-cosine+threshold stays default.

## 2026-07-02 — Vertical slice built (offline half proven; fetch awaits key)

- **Done:** Scaffolded the whole pipeline with hard stage boundaries (music-project.md): `config.py` (all knobs/paths/thresholds), `db/schema.sql` (raw_responses, albums, album_tags, tag_global, edges), and stages `fetch → clean → features → similarity → export` under `pipeline/`, each runnable alone + orchestrated by `run.py`. One HTTP wrapper (`http_client.py`) does rate-limit + retry/backoff + verbatim cache + `logs/fetch_errors.jsonl`. d3-force frontend (`frontend/`, d3 vendored offline) with live weighted-sum, metric/weighting/mode toggles, threshold+k sliders, zoom-adaptive label thinning.
- **Proven:** `tools/smoke.py` seeds synthetic 3-cluster data into a temp db and runs features→similarity→export: schema valid, intra-cluster cosine 1.000 vs inter 0.000, blackgaze bridge links both clusters, null-year path exercised. `tests/test_identity.py` (ADR-007 dedup) 6/6 green. `graph.js` node-syntax clean.
- **Decisions honored:** raw-cosine is the live acceptance axis; idf/jaccard computed too (cheap, gives Cruz the A/B toggles) but raw-cosine is the default. Export contract = floor OR top-15 (ADR-004) implemented in similarity stage. Windows console forced UTF-8 (␟ separator).
- **Seed set:** `data/albums.csv` — ~40 hand-picked albums with deliberate bridges (blackgaze shoegaze↔black-metal; post-rock shoegaze↔ambient) for real acceptance ground truth.
- **Broken/unstarted:** fetch + clean never hit a live API yet — **need the Last.fm key in `.env`** (`.env.example` present). `frontend/graph.json` is a synthetic placeholder until the real run overwrites it. No screenshot yet (frontend needs a static server + real data). Repo git-initialized, scaffold committed on `main`.
- **Next step:** Cruz pastes `LASTFM_API_KEY` → `python run.py` (real ~40-album fetch) → run `tools/neighbors.py` for acceptance Check 1 + serve `frontend/` and eyeball Check 2. Then flip on the wired-but-dark toggles / fill acceptance specifics.

## 2026-07-02 — Design grill: similarity/graph core locked

- **Done:** Grilled the full fetch→similarity→graph trunk to shared understanding. 11 decisions locked and captured as ADR-001..007 (`docs/adr/`); reversed the whitelist→blacklist standing decision; updated `music-project.md` to match.
- **Key calls:** dual genre metric (cosine+jaccard) × raw+IDF, corpus-aware IDF from Last.fm global tag freqs; 3 edge-draw modes client-side; export floor OR per-node top-15 (no kNN starvation); conservative MB year matching (missing > wrong); normalized (artist,album) node key; blacklist+IDF over whitelist.
- **Build discipline:** thin path, full-shape schema — first run is raw-cosine + year + threshold only; idf/jaccard/kNN/mutual wired-but-dark until end-to-end proves out.
- **Frontend/render contract grilled + captured** (ADR-008, `docs/export-schema.md`, `docs/acceptance-thin-slice.md`): self-describing `meta`+`nodes`+`edges` JSON, nodes by string id; node color = dominant post-blacklist tag (interim community color); zoom-adaptive labels (viewport-local density trigger — required so the acceptance checklist is runnable cluster-by-cluster); d3-force with link strength ∝ similarity, tuned live. `sim_year: null` per edge = client drops year term + renormalizes.
- **Acceptance test defined:** neighbor table (metric) AND visual checklist (graph) — both must pass; the split localizes which stage broke. Template in `docs/acceptance-thin-slice.md`, fill specifics once the curated ~100 exists.
- **Not yet grilled:** Elo scoring workstream (pair selection, K-factor, cold start, sequencing vs graph); coverage-audit tooling.
- **Broken/unstarted:** no code yet. Repo not git-initialized; no `.gitignore`, no config module, no cache.db schema. Curated ~100 album list not yet chosen (blocks acceptance-test specifics).
- **Next step:** either (a) grill the Elo scoring branch, or (b) start the vertical slice — scaffold repo (git init, .gitignore, config module, cache.db schema) then fetcher-agent for the Last.fm client on the curated ~100. Design tree trunk + frontend are fully resolved; scoring is the only major un-grilled branch.
