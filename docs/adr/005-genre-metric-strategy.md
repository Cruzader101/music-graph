# ADR-005 — Genre metric strategy: dual metric + corpus-aware IDF

**Status:** Accepted (2026-07-02)

## Context
`sim_genre` operates on Last.fm weighted tag vectors (top tag = 100, per-album normalized).
Two open questions had no single right answer, only tradeoffs the eye must judge:

1. **Metric.** Weighted **cosine** is scale-invariant and reduces to one sparse matmul
   `normalize(M) @ normalize(M).T`, but ignores magnitude — a richly-tagged and a sparsely-tagged
   album pointing the same direction score high. Weighted **Jaccard** (`Σmin/Σmax`) treats extra
   tags as *distinctness*, which may better match intuition, but is scale-sensitive and not a
   single matmul. Cruz specifically wants to see whether "more tags = more distinct" holds.
2. **Frequency weighting.** Last.fm weights are per-album only; ubiquitous tags (`rock`, `indie`)
   dominate raw similarity. IDF fixes this — but IDF computed over the ~100 curated albums would
   punish genres the curator *deliberately* overloaded (30 shoegaze albums → "shoegaze" looks
   common → suppressed). Backwards.

## Decision
- **Compute both metrics** (cosine and Jaccard) for every pair; export both per edge; frontend
  radio selects which feeds the weighted sum. **Union export** (ADR-004 floor takes the max over
  all genre values) so the edge set is identical across the toggle — comparing scores, not
  filtering artifacts.
- **Apply IDF, corpus-aware:** df comes from **Last.fm global tag frequencies** (`tag.getInfo`
  taggings/reach), not the local corpus. Store both raw and IDF-weighted vectors; expose a second
  `[raw | idf]` toggle.
- Net: 4 genre values per edge — `sim_genre_{raw,idf}_{cosine,jaccard}`.

## Consequences
- One extra cached `tag.getInfo` call per distinct tag (~hundreds total), on the existing Last.fm
  client + `cache.db`.
- Edges carry 4 genre floats + `sim_year`. Cheap; all precomputed.
- Jaccard is the costly axis at scale (no single matmul) — profile it first if O(n²) bites.
- **First run populates raw-cosine only**; jaccard + idf are wired-but-dark until end-to-end
  proves out (build cut line).
- Divides labor with the blacklist (ADR-003): IDF suppresses common-generic tags; blacklist kills
  rare-idiosyncratic junk that IDF would otherwise amplify.
