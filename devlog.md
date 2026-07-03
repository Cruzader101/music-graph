# Devlog

## 2026-07-02 — Design grill: similarity/graph core locked

- **Done:** Grilled the full fetch→similarity→graph trunk to shared understanding. 11 decisions locked and captured as ADR-001..007 (`docs/adr/`); reversed the whitelist→blacklist standing decision; updated `music-project.md` to match.
- **Key calls:** dual genre metric (cosine+jaccard) × raw+IDF, corpus-aware IDF from Last.fm global tag freqs; 3 edge-draw modes client-side; export floor OR per-node top-15 (no kNN starvation); conservative MB year matching (missing > wrong); normalized (artist,album) node key; blacklist+IDF over whitelist.
- **Build discipline:** thin path, full-shape schema — first run is raw-cosine + year + threshold only; idf/jaccard/kNN/mutual wired-but-dark until end-to-end proves out.
- **Frontend/render contract grilled + captured** (ADR-008, `docs/export-schema.md`, `docs/acceptance-thin-slice.md`): self-describing `meta`+`nodes`+`edges` JSON, nodes by string id; node color = dominant post-blacklist tag (interim community color); zoom-adaptive labels (viewport-local density trigger — required so the acceptance checklist is runnable cluster-by-cluster); d3-force with link strength ∝ similarity, tuned live. `sim_year: null` per edge = client drops year term + renormalizes.
- **Acceptance test defined:** neighbor table (metric) AND visual checklist (graph) — both must pass; the split localizes which stage broke. Template in `docs/acceptance-thin-slice.md`, fill specifics once the curated ~100 exists.
- **Not yet grilled:** Elo scoring workstream (pair selection, K-factor, cold start, sequencing vs graph); coverage-audit tooling.
- **Broken/unstarted:** no code yet. Repo not git-initialized; no `.gitignore`, no config module, no cache.db schema. Curated ~100 album list not yet chosen (blocks acceptance-test specifics).
- **Next step:** either (a) grill the Elo scoring branch, or (b) start the vertical slice — scaffold repo (git init, .gitignore, config module, cache.db schema) then fetcher-agent for the Last.fm client on the curated ~100. Design tree trunk + frontend are fully resolved; scoring is the only major un-grilled branch.
