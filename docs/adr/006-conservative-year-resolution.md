# ADR-006 — Conservative MusicBrainz year resolution (missing over wrong)

**Status:** Accepted (2026-07-02)

## Context
Year is half the similarity model. MusicBrainz resolution searches `artist + album` and returns
a *scored list* of release-groups. "Take the top match" is dangerous: the top hit can be a live
album, a compilation, a deluxe reissue registered as its own release-group, or a fuzzy artist
collision. Grabbing a reissue's date stamps a 1985 album as 2011 and mis-places the node in the
wrong era entirely.

Key asymmetry: **a wrong year mis-places a node; a missing year degrades gracefully.** The
pipeline already drops the year term and renormalizes weights for missing-year pairs (ADR-002),
so the node still renders in the right genre neighborhood. A wrong year has no such safety net.

## Decision
- Match only if **fuzzy(artist) passes AND the MusicBrainz search score clears a floor**.
- Among qualifying release-groups, take the **earliest `first-release-date`** (defeats
  reissues/remasters registered as separate release-groups).
- If nothing qualifies, set `status: year_unresolved` — drop the year term, renormalize — rather
  than guess. Every unresolved case is logged for the coverage audit.

## Consequences
- Wrong-year risk minimized; coverage slightly lower but every gap is honest and auditable.
- Year resolution stays off the critical path for node existence (album still renders without a year).
- Thresholds (fuzzy tolerance, score floor) are config, tunable from audit feedback.
- Manual confirmation of ambiguous matches is explicitly deferred — not part of the one-shot slice.
