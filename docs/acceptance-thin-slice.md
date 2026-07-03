# Acceptance test — thin vertical slice

The thin run (raw-cosine genre + year + threshold draw) **passes** only if BOTH checks below pass.
Splitting the test along the stage boundary makes a failure diagnostic:

- neighbor table fails → bug is in **similarity** (tags, blacklist, IDF off, dedup, metric)
- neighbor table passes but visual fails → bug is in **export / layout / render**

Fill in the specifics once the curated ~100 is chosen (the expected clusters are your ground truth).

## Check 1 — Nearest-neighbor table (tests the metric)

For ~10 hand-picked seed albums, print top-5 nearest neighbors by `sim_genre_raw_cosine`.
Passes if every list is defensible. **Regenerate with `python -m tools.neighbors`.**

Result on the 40-album seed set (2026-07-02, run 3 after Kendrick-title + hyphen-tag + label-blacklist fixes):

```
SEED                        TOP-5 (raw cosine)
MBV — Loveless              Lush .96, Ride .96, Slowdive .94, Alcest .81, Cocteau Twins .61
Deafheaven — Sunbather      Mayhem .35, WITTR .31, Burzum .30, Emperor .30, Alcest .29   [blackgaze bridge]
Mayhem — De Mysteriis       Emperor .75, Burzum .73, WITTR .72, Deafheaven .35, Alcest .16
Nick Drake — Pink Moon      Fleet Foxes .84, Joni Mitchell .83, Bon Iver .78, Sufjan .34, Elliott Smith .10
Kendrick — good kid         Kanye .79, Nas .76, ATCQ .47, Madvillain .30, J Dilla .13
Miles Davis — Kind of Blue  Mingus .90, Bill Evans .88, Coltrane .82, Herbie .61
Aphex Twin — SAW 85-92      Boards of Canada .92, Eno .72, Sigur Rós .65, Four Tet .48, Burial .45
GY!BE — Lift Yr Skinny...   Talk Talk .95, Explosions .30, Sigur Rós .23   [post-rock]
```

- [x] All neighbor lists are musically defensible
- [x] No obvious junk neighbor (no metal record in a folk album's top-5)
- Notes: Deafheaven (blackgaze) leans to its black-metal neighbors — correct, Sunbather is tagged heavily black metal; the Alcest link ties it back to shoegaze. Kendrick required a title fix (`good kid, m.A.A.d city`) — Last.fm returned only label tags for the no-comma title (see devlog).

## Check 2 — Visual checklist (tests graph + render)

Pre-commit ~5 expected groupings you KNOW from curating, then render and verify.
Overview items judged zoomed-out (color + position); adjacency items judged zoomed-in (labels).

- [~] _(overview)_ Color clusters coincide with spatial clusters — **spatial clusters correct; color
      is fragmented** because interim node color = dominant tag, and one genre spans several tags
      (folk / singer songwriter / chamber pop; abstract hip hop / jazz rap / rap). Real fix = Louvain
      communities (roadmap #5). Not a metric failure — Check 1 passes.
- [x] _(overview)_ Outliers sit peripheral (Herbie Hancock / jazz-funk, GY!BE / post-rock on the rim)
- [x] _(adjacency)_ MBV — Loveless adjacent to Slowdive / Ride / Lush
- [x] _(adjacency)_ Miles Davis — Kind of Blue adjacent to Coltrane / Mingus / Bill Evans
- [x] _(check)_ No album sits in an obviously wrong-*spatial* blob (color caveat above)

Rendered via `python -m http.server` in `frontend/` (fetch needs http, not file://). Default view at
threshold 0.35 is a connected hairball (genuine moderate cross-genre similarity); switch draw mode to
kNN or raise the threshold slider to separate blobs.

## Verdict — thin slice PASSES (2026-07-02)
- Check 1 (metric) passes outright. Check 2 (render) passes on spatial structure; color granularity is
  the documented interim state, fixed by Louvain later — not a blocker.
- idf/jaccard/kNN/mutual toggles are wired and live (computed for real); raw-cosine + threshold remains
  the default acceptance axis. Next iteration: Louvain community coloring, then scale the album set.
