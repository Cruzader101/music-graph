# Acceptance test — thin vertical slice

The thin run (raw-cosine genre + year + threshold draw) **passes** only if BOTH checks below pass.
Splitting the test along the stage boundary makes a failure diagnostic:

- neighbor table fails → bug is in **similarity** (tags, blacklist, IDF off, dedup, metric)
- neighbor table passes but visual fails → bug is in **export / layout / render**

Fill in the specifics once the curated ~100 is chosen (the expected clusters are your ground truth).

## Check 1 — Nearest-neighbor table (tests the metric)

For ~10 hand-picked seed albums, print top-5 nearest neighbors by `sim_genre_raw_cosine`.
Passes if every list is defensible.

```
SEED                     TOP-5 NEIGHBORS (raw cosine)
<album 1>                ...
<album 2>                ...
... (10 seeds)
```

- [ ] All 10 neighbor lists are musically defensible
- [ ] No obvious junk neighbor (a metal record in a folk album's top-5)

## Check 2 — Visual checklist (tests graph + render)

Pre-commit ~5 expected groupings you KNOW from curating, then render and verify.
Overview items judged zoomed-out (color + position); adjacency items judged zoomed-in (labels).

- [ ] _(overview)_ Color clusters coincide with spatial clusters (dominant-tag color ≈ layout blob)
- [ ] _(overview)_ The outlier/lonely album sits peripheral, not buried in a blob
- [ ] _(adjacency)_ `<album A>` is adjacent to `<album B>`   ← fill from your set
- [ ] _(adjacency)_ `<album C>` is adjacent to `<album D>`
- [ ] _(check)_ No album sits in an obviously wrong-colored blob

## Verdict
- Both checks pass → slice works; enable the wired-but-dark toggles (idf, jaccard, kNN/mutual, sliders).
- Either fails → use the split above to localize the stage, fix, re-run.
